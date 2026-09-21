#include "WarCapitalProofSubsystem.h"
#include "WarWorldEditSubsystem.h"
#include "WarWorldEditCatalog.h"
#include "WarWorldEditPlacement.h"
#include "WarPlayerController.h"
#include "WarWorldEditWidget.h"
#include "UObject/UObjectIterator.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/Pawn.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UWarCapitalProofSubsystem::RunConstructionRowProof()
{
    auto* Player=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Editor=GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    FString Error;
    const auto Check=[this](bool Passed,const FString& Message) { if (!Passed) Finish(false,Message); return Passed; };
    if (!Check(Player && Player->GetPawn() && Editor,TEXT("Missing native row proof world."))) return;
    const bool bReload=FParse::Param(FCommandLine::Get(),TEXT("WarCapitalReloadProof"));
    const int32 BaselineCount=Editor->GetHistory().GetObjects().Num();
    if (bReload && !Check(Editor->LoadDraft(Player,0,Error),TEXT("Row draft reload failed: ")+Error)) return;
    FName TemplateId;
    for (const auto& Entry : WarWorldEditCatalog::Build(Editor->GetHistory().GetBaselineObjects()))
        if (const auto* Actor=Cast<AStaticMeshActor>(Editor->GetObjectActor(Entry.TemplateId)))
            if (const UStaticMesh* Mesh=Actor->GetStaticMeshComponent()->GetStaticMesh())
                if (Mesh->GetName().EndsWith(TEXT("Stone_Wall_01"))) { TemplateId=Entry.TemplateId; break; }
    if (!Check(!TemplateId.IsNone(),TEXT("Authored wall module is missing."))) return;
    auto* TemplateActor=Cast<AStaticMeshActor>(Editor->GetObjectActor(TemplateId));
    const UStaticMesh* Mesh=TemplateActor->GetStaticMeshComponent()->GetStaticMesh();
    FTransform Basis=Editor->GetHistory().Find(TemplateId)->Transform;
    if (!bReload)
    {
        Basis.SetRotation(FRotator(0,45,0).Quaternion());
        if (!Check(Editor->Edit(Player,TemplateId,Basis,false,0,Error),TEXT("Could not rotate the authored row template."))) return;
        const int32 Revision=Editor->GetHistory().GetRevision();
        FName Rejected;
        if (!Check(!Editor->CreateRow(nullptr,TemplateId,3,false,25,100,Revision,Rejected,Error)
            && !Editor->CreateRow(Player,TemplateId,33,false,25,100,Revision,Rejected,Error)
            && !Editor->CreateRow(Player,TemplateId,3,false,-1,100,Revision,Rejected,Error)
            && !Editor->CreateRow(Player,TemplateId,3,false,25,100,Revision-1,Rejected,Error)
            && !Editor->CreateRow(Player,TemplateId,32,false,10000,100,Revision,Rejected,Error)
            && Editor->GetHistory().GetRevision()==Revision && Editor->GetHistory().GetObjects().Num()==BaselineCount,
            TEXT("Rejected or unsupported row left partial construction."))) return;
        Player->ServerCreateWorldRow(TemplateId,3,false,25,100,Revision);
        if (!Check(Editor->GetHistory().GetRevision()==Revision+1
            && Editor->GetHistory().GetObjects().Num()==BaselineCount+3,TEXT("Row RPC failed: ")+Player->GetWorldEditMessage())) return;
        if (!Check(Editor->Undo(Player,false,Revision+1,Error)
            && Editor->GetHistory().GetObjects().Num()==BaselineCount,TEXT("One undo did not remove the whole row."))) return;
        if (!Check(Editor->Undo(Player,true,Revision+2,Error),TEXT("Row redo failed."))) return;
    }
    const FVector Direction=Basis.GetRotation().RotateVector(FVector::ForwardVector);
    const double Spacing=Mesh->GetBoundingBox().GetSize().X*FMath::Abs(Basis.GetScale3D().X)+25;
    const APawn* Pawn=Player->GetPawn();
    const FVector Origin=WarWorldEditPlacement::SnapHorizontal(Pawn->GetActorLocation()+Pawn->GetActorForwardVector()*2000,100);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WarRowProof),false);
    Query.AddIgnoredActor(Pawn); Query.AddIgnoredActor(TemplateActor);
    TArray<const FWarWorldEditObject*> Created;
    for (const auto& Row : Editor->GetHistory().GetObjects()) if (!Row.TemplateId.IsNone())
    { Created.Add(&Row); Query.AddIgnoredActor(Editor->GetObjectActor(Row.Id)); }
    if (!Check(Created.Num()==3,TEXT("Row has a missing or extra model."))) return;
    Created.Sort([&](const auto& A,const auto& B) {
        return FVector::DotProduct(A.Transform.GetLocation(),Direction)<FVector::DotProduct(B.Transform.GetLocation(),Direction); });
    for (int32 Index=0; Index<Created.Num(); ++Index)
    {
        const auto& Row=*Created[Index];
        const auto* Actor=Cast<AStaticMeshActor>(Editor->GetObjectActor(Row.Id));
        if (!Check(Actor && Row.TemplateId==TemplateId,TEXT("Row lost an authored model identity."))) return;
        const auto* Component=Actor->GetStaticMeshComponent();
        const auto Bounds=Component->Bounds;
        const FVector Target=Origin+Direction*Spacing*Index;
        FHitResult Hit;
        if (!Check(GetWorld()->LineTraceSingleByChannel(Hit,Target+FVector(0,0,10000),Target-FVector(0,0,20000),ECC_Visibility,Query)
            && FVector::Dist2D(Bounds.Origin,Target)<.1 && FMath::Abs(Bounds.Origin.Z-Bounds.BoxExtent.Z-Hit.ImpactPoint.Z)<.1
            && Component->GetStaticMesh()==Mesh && Component->GetCollisionProfileName()==TEXT("BlockAll")
            && Component->IsRegistered() && Component->IsVisible() && !Actor->IsHidden()
            && Row.Transform.GetRotation().Equals(Basis.GetRotation()) && Row.Transform.GetScale3D().Equals(Basis.GetScale3D()),
            TEXT("Row spacing, contact, model, orientation or collision changed."))) return;
    }
    if (!bReload && !Check(Editor->SaveDraft(Player,Editor->GetHistory().GetRevision(),Error),TEXT("Row draft save failed: ")+Error)) return;
    if (FParse::Param(FCommandLine::Get(),TEXT("WarProofScreenshot")))
    {
        Player->ToggleWorldEditor(); Player->ClientWorldObjectCreated(Created[0]->Id);
        for (TObjectIterator<UWarWorldEditWidget> It; It; ++It)
            if (It->GetOwningPlayer()==Player) It->ExpandRepeatedConstruction();
    }
    bConstructionRowVerified=true;
    Finish(true,TEXT("Atomic row construction, oriented spacing, support, undo/redo and persistence verified."));
}
