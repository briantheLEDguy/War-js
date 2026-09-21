#include "WarWorldEditSubsystem.h"
#include "WarWorldEditPlacement.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"

bool UWarWorldEditSubsystem::CreateRow(APlayerController* Controller, const FName Id, const int32 Count,
    const bool bAlongY, const double Gap, const double Grid, const int32 Revision, FName& CreatedId, FString& Error)
{
    CreatedId = NAME_None;
    if (!Ready(Controller,Error)) return false;
    if (Revision != History.GetRevision()) { Error=TEXT("Draft changed; refresh before placing a row."); return false; }
    if (Count<2 || Count>32 || !FMath::IsFinite(Grid) || Grid<0 || Grid>10000)
    { Error=TEXT("A row requires 2-32 pieces and a valid grid."); return false; }
    const auto* Row=History.Find(Id);
    if (!Row || Row->bHidden) { Error=TEXT("Select a visible model to repeat."); return false; }
    const FName TemplateId=Row->TemplateId.IsNone() ? Row->Id : Row->TemplateId;
    const auto* Template=Templates.Find(TemplateId);
    if (!Template || !Template->Mesh.IsValid()) { Error=TEXT("Required authored model is unavailable."); return false; }
    const FBox Bounds=Template->Mesh->GetBoundingBox();
    const auto Step=WarWorldEditPlacement::RowStep(Row->Transform,Bounds,bAlongY,Gap);
    if (!Step.IsSet()) { Error=TEXT("Choose a horizontal model axis and a gap from 0 to 100 metres."); return false; }
    const APawn* Pawn=Controller->GetPawn();
    const FVector Origin=WarWorldEditPlacement::SnapHorizontal(Pawn->GetActorLocation()+Pawn->GetActorForwardVector()*2000,Grid);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WarBuilderRow),false);
    Query.AddIgnoredActor(Pawn); Query.AddIgnoredActor(GetObjectActor(Id));
    TArray<FWarWorldEditCreation> Additions;
    // Resolve every support before spawning; a missing last surface must not leave a partial row.
    for (int32 Index=0; Index<Count; ++Index)
    {
        const FVector Target=Origin+Step.GetValue()*Index;
        FHitResult Hit;
        if (!GetWorld()->LineTraceSingleByChannel(Hit,Target+FVector(0,0,10000),Target-FVector(0,0,20000),ECC_Visibility,Query))
        { Error=FString::Printf(TEXT("No support beneath row piece %d. Nothing was placed."),Index+1); return false; }
        const auto Transform=WarWorldEditPlacement::AtSurface(Row->Transform,Bounds,Hit.ImpactPoint);
        if (!Transform.IsSet()) { Error=TEXT("The row exceeds supported world bounds. Nothing was placed."); return false; }
        const FName NewId(*(TEXT("gm_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
        Additions.Add({NewId,TemplateId,Transform.GetValue()});
    }
    auto Next=History;
    if (!Next.CreateBatch(Additions,Revision,Error) || !ApplyHistory(MoveTemp(Next),Error)) return false;
    CreatedId=Additions[0].Id; return true;
}

bool UWarWorldEditSubsystem::CreateInFront(APlayerController* Controller, const FName TemplateId,
    const double Grid, const double Angle, const int32 Revision, FName& CreatedId, FString& Error)
{
    CreatedId = NAME_None;
    if (!Ready(Controller, Error)) return false;
    if (Revision != History.GetRevision()) { Error = TEXT("Draft changed; refresh before placing."); return false; }
    if (!FMath::IsFinite(Grid) || !FMath::IsFinite(Angle) || Grid < 0 || Grid > 10000 || Angle < 0 || Angle > 360)
    { Error = TEXT("Invalid placement grid or turn step."); return false; }
    const auto* Template = Templates.Find(TemplateId);
    const auto* Original = History.GetBaselineObjects().FindByPredicate([TemplateId](const auto& Row) { return Row.Id == TemplateId; });
    if (!Template || !Template->Mesh.IsValid() || !Original)
    { Error = TEXT("Required authored model is unavailable."); return false; }
    const APawn* Pawn = Controller->GetPawn();
    const FVector Target = WarWorldEditPlacement::SnapHorizontal(Pawn->GetActorLocation() + Pawn->GetActorForwardVector()*2000, Grid);
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(WarBuilderPlace), false); Query.AddIgnoredActor(Pawn);
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Target + FVector(0,0,10000), Target - FVector(0,0,20000), ECC_Visibility, Query))
    { Error = TEXT("No supporting surface ahead. Move closer to the city or choose another direction."); return false; }
    const FTransform Basis = WarWorldEditPlacement::SnapTransform(Original->Transform, 0, Angle);
    const auto Transform = WarWorldEditPlacement::AtSurface(Basis, Template->Mesh->GetBoundingBox(), Hit.ImpactPoint);
    if (!Transform.IsSet()) { Error = TEXT("The model cannot be placed within the supported world bounds."); return false; }
    return Create(Controller, TemplateId, Transform.GetValue(), Revision, CreatedId, Error);
}

bool UWarWorldEditSubsystem::DropToSurface(APlayerController* Controller, const FName Id, const int32 Revision, FString& Error)
{
    if (!Ready(Controller, Error)) return false;
    if (Revision != History.GetRevision()) { Error = TEXT("Draft changed; refresh before dropping."); return false; }
    const auto* Row = History.Find(Id);
    auto* Actor = Cast<AStaticMeshActor>(GetObjectActor(Id));
    if (!Row || Row->bHidden || !Actor || !Actor->GetStaticMeshComponent()->GetStaticMesh())
    { Error = TEXT("Select a visible authored model to drop."); return false; }
    const UStaticMesh* Mesh = Actor->GetStaticMeshComponent()->GetStaticMesh();
    const FBox Bounds = Mesh->GetBoundingBox().TransformBy(Row->Transform);
    const FVector Start(Bounds.GetCenter().X, Bounds.GetCenter().Y, Bounds.Min.Z + 1);
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(WarBuilderDrop), false);
    Query.AddIgnoredActor(Actor); Query.AddIgnoredActor(Controller->GetPawn());
    // Start at the bottom, so overhead floors cannot pull a selected prop upstairs.
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Start, Start - FVector(0,0,20000), ECC_Visibility, Query))
    { Error = TEXT("No supporting surface below. Raise the model if it is buried, then try again."); return false; }
    const auto Transform = WarWorldEditPlacement::AtSurface(Row->Transform, Mesh->GetBoundingBox(), Hit.ImpactPoint);
    if (!Transform.IsSet()) { Error = TEXT("The model cannot be dropped within the supported world bounds."); return false; }
    return Edit(Controller, Id, Transform.GetValue(), false, Revision, Error);
}
