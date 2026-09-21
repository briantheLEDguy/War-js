#include "WarCapitalProofSubsystem.h"
#include "WarWorldEditSubsystem.h"
#include "WarWorldEditCatalog.h"
#include "WarWorldEditPlacement.h"
#include "WarPlayerController.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/Pawn.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UWarCapitalProofSubsystem::RunSurfacePlacementProof()
{
    auto* Player = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    FString Error;
    const auto Check = [this](bool Passed, const FString& Message) { if (!Passed) Finish(false,Message); return Passed; };
    if (!Check(Player && Player->GetPawn() && Editor, TEXT("Missing placement proof world."))) return;
    const APawn* Pawn = Player->GetPawn();
    const auto Catalog = WarWorldEditCatalog::Build(Editor->GetHistory().GetBaselineObjects());
    if (!Check(!Catalog.IsEmpty(),TEXT("No authored models in the placement catalog."))) return;
    const FVector Target = WarWorldEditPlacement::SnapHorizontal(Pawn->GetActorLocation()+Pawn->GetActorForwardVector()*2000,100);
    const auto CheckContact = [&](const FName Id, const FVector Expected) {
        auto* Actor = Cast<AStaticMeshActor>(Editor->GetObjectActor(Id));
        const auto* Row = Editor->GetHistory().Find(Id);
        if (!Check(Actor && Row && Actor->GetStaticMeshComponent()->GetStaticMesh(),TEXT("Placed authored model missing."))) return false;
        const auto Bounds = Actor->GetStaticMeshComponent()->Bounds;
        return Check(FVector::Dist2D(Bounds.Origin,Expected)<.1 && FMath::Abs(Bounds.Origin.Z-Bounds.BoxExtent.Z-Expected.Z)<.1
            && Actor->GetActorTransform().Equals(Row->Transform,.001), TEXT("Imported pivot moved the visible bounds off the selected surface."));
    };
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WarSurfaceProof),false); Query.AddIgnoredActor(Pawn);
    const int32 BaselineCount = Editor->GetHistory().GetObjects().Num();
    if (FParse::Param(FCommandLine::Get(), TEXT("WarCapitalReloadProof")))
    {
        const bool Loaded = Editor->LoadDraft(Player,0,Error);
        if (!Check(Loaded && Editor->GetHistory().GetObjects().Num()==BaselineCount+1, TEXT("Surface draft reload failed: ")+Error)) return;
        const auto* Created = Editor->GetHistory().GetObjects().FindByPredicate([](const auto& Row) { return !Row.TemplateId.IsNone(); });
        if (!Check(Created!=nullptr,TEXT("Reload lost the placed model."))) return;
        Query.AddIgnoredActor(Editor->GetObjectActor(Created->Id));
        FHitResult Hit;
        const bool Found = GetWorld()->LineTraceSingleByChannel(Hit,Target+FVector(0,0,10000),Target-FVector(0,0,20000),ECC_Visibility,Query);
        if (!Check(Found,TEXT("Reload lost the support surface.")) || !CheckContact(Created->Id,Hit.ImpactPoint)) return;
        if (FParse::Param(FCommandLine::Get(),TEXT("WarProofScreenshot")))
        { Player->ToggleWorldEditor(); Player->ClientWorldObjectCreated(Created->Id); }
        bSurfacePlacementVerified=true; Finish(true,TEXT("Surface-aligned construction survived a fresh process.")); return;
    }
    FName Rejected;
    if (!Check(!Editor->CreateInFront(nullptr,Catalog[0].TemplateId,100,90,0,Rejected,Error)
        && !Editor->CreateInFront(Player,TEXT("missing_model"),100,90,0,Rejected,Error)
        && !Editor->CreateInFront(Player,Catalog[0].TemplateId,-1,90,0,Rejected,Error)
        && !Editor->CreateInFront(Player,Catalog[0].TemplateId,100,90,99,Rejected,Error)
        && Editor->GetHistory().GetRevision()==0,TEXT("Invalid placement changed the draft."))) return;
    FName FinalId; FVector FinalContact = FVector::ZeroVector;
    for (int32 Index=0; Index<Catalog.Num(); ++Index)
    {
        FHitResult Hit;
        if (!Check(GetWorld()->LineTraceSingleByChannel(Hit,Target+FVector(0,0,10000),Target-FVector(0,0,20000),ECC_Visibility,Query),
            TEXT("No native placement surface."))) return;
        const int32 Revision=Editor->GetHistory().GetRevision();
        Player->ServerPlaceWorldObject(Catalog[Index].TemplateId,100,90,Revision);
        if (!Check(Editor->GetHistory().GetObjects().Num()==BaselineCount+1,TEXT("Place-model RPC failed: ")+Player->GetWorldEditMessage())) return;
        const auto* Created=Editor->GetHistory().GetObjects().FindByPredicate([](const auto& Row){return !Row.TemplateId.IsNone();});
        if (!Check(Created!=nullptr,TEXT("Place-model RPC lost its identity.")) || !CheckContact(Created->Id,Hit.ImpactPoint)) return;
        auto* Actor=Cast<AStaticMeshActor>(Editor->GetObjectActor(Created->Id));
        auto* Original=Cast<AStaticMeshActor>(Editor->GetObjectActor(Catalog[Index].TemplateId));
        if (!Check(Original && Actor->GetStaticMeshComponent()->GetStaticMesh()==Original->GetStaticMeshComponent()->GetStaticMesh()
            && Actor->GetStaticMeshComponent()->GetCollisionProfileName()==TEXT("BlockAll"),TEXT("Surface placement changed model or collision."))) return;
        ++SurfaceModelsVerified; FinalId=Created->Id; FinalContact=Hit.ImpactPoint;
        if (Index+1<Catalog.Num() && !Check(Editor->Undo(Player,false,Editor->GetHistory().GetRevision(),Error),TEXT("Placement undo failed."))) return;
    }
    const FTransform Grounded=Editor->GetHistory().Find(FinalId)->Transform;
    FTransform Elevated=Grounded; Elevated.AddToTranslation(FVector(0,0,400));
    if (!Check(Editor->Edit(Player,FinalId,Elevated,false,Editor->GetHistory().GetRevision(),Error),TEXT("Could not raise placed model."))) return;
    const int32 BeforeDrop=Editor->GetHistory().GetRevision();
    Player->ServerDropWorldObject(FinalId,BeforeDrop-1);
    if (!Check(Editor->GetHistory().GetRevision()==BeforeDrop,TEXT("Stale surface drop changed the draft."))) return;
    Player->ServerDropWorldObject(FinalId,BeforeDrop);
    if (!CheckContact(FinalId,FinalContact)) return;
    if (!Check(Editor->Undo(Player,false,Editor->GetHistory().GetRevision(),Error)
        && Editor->GetHistory().Find(FinalId)->Transform.Equals(Elevated,.001),TEXT("Drop undo did not restore height."))) return;
    if (!Check(Editor->Undo(Player,true,Editor->GetHistory().GetRevision(),Error),TEXT("Drop redo failed.")) || !CheckContact(FinalId,FinalContact)) return;
    if (!Check(Editor->Edit(Player,FinalId,Grounded,true,Editor->GetHistory().GetRevision(),Error),TEXT("Hide fixture failed."))) return;
    int32 RejectedRevision=Editor->GetHistory().GetRevision();
    if (!Check(!Editor->DropToSurface(Player,FinalId,RejectedRevision,Error)
        && Editor->GetHistory().GetRevision()==RejectedRevision,TEXT("A hidden model accepted a surface drop."))) return;
    if (!Check(Editor->Undo(Player,false,RejectedRevision,Error),TEXT("Hide fixture undo failed."))) return;
    FTransform BelowWorld=Grounded; BelowWorld.SetLocation(FVector(90000,90000,-90000));
    if (!Check(Editor->Edit(Player,FinalId,BelowWorld,false,Editor->GetHistory().GetRevision(),Error),TEXT("No-support fixture failed."))) return;
    RejectedRevision=Editor->GetHistory().GetRevision();
    if (!Check(!Editor->DropToSurface(Player,FinalId,RejectedRevision,Error)
        && Editor->GetHistory().GetRevision()==RejectedRevision
        && Editor->GetHistory().Find(FinalId)->Transform.Equals(BelowWorld),TEXT("Missing support changed the model."))) return;
    if (!Check(Editor->Undo(Player,false,RejectedRevision,Error),TEXT("No-support fixture undo failed.")) || !CheckContact(FinalId,FinalContact)) return;
    const bool Saved=Editor->SaveDraft(Player,Editor->GetHistory().GetRevision(),Error);
    if (!Check(Saved,TEXT("Surface placement save failed: ")+Error)) return;
    if (FParse::Param(FCommandLine::Get(),TEXT("WarProofScreenshot")))
    { Player->ToggleWorldEditor(); Player->ClientWorldObjectCreated(FinalId); }
    bSurfacePlacementVerified=true; Finish(true,TEXT("All catalog models: bounds-aware place RPC, drop RPC, stale rejection, undo/redo and save verified."));
}
