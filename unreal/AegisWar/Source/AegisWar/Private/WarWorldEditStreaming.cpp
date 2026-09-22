#include "WarWorldEditSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Level.h"
#include "Engine/World.h"

ULevel* UWarWorldEditSubsystem::LoadedLevel(FName Package) const
{
    for (ULevel* Level : GetWorld()->GetLevels())
        if (Level && Level->GetOutermost()->GetFName() == Package && Level->bIsVisible) return Level;
    return nullptr;
}
void UWarWorldEditSubsystem::LevelRemoved(ULevel* Level, UWorld* World)
{
    if (World != GetWorld() || !Level) return;
    for (auto& Pair : Actors)
        if (Pair.Value.IsValid() && Pair.Value->GetLevel() == Level) Pair.Value.Reset();
}
void UWarWorldEditSubsystem::LevelAdded(ULevel* Level, UWorld* World)
{
    if (World != GetWorld() || !Level || !bInitialized) return;
    const FName Package = Level->GetOutermost()->GetFName();
    bool bRelevant = false;
    for (const auto& Pair : BaselineLevels) bRelevant |= Pair.Value == Package;
    if (!bRelevant) return;
    TMap<FName, TWeakObjectPtr<AActor>> Rebound;
    for (AActor* Actor : Level->Actors)
    {
        if (!IsValid(Actor) || !Actor->ActorHasTag(TEXT("WarCapitalBuilding"))) continue;
        FName Id; FString Hash;
        for (FName Tag : Actor->Tags)
        {
            const FString Text = Tag.ToString();
            if (Text.StartsWith(TEXT("WarWorldObject_")))
            {
                if (!Id.IsNone()) { StreamingConflict = TEXT("Ambiguous GM identity after zone reload."); return; }
                Id = FName(*Text.RightChop(15));
            }
            else if (Text.StartsWith(TEXT("WarModelSha256_")))
            {
                if (!Hash.IsEmpty()) { StreamingConflict = TEXT("Ambiguous GM provenance after zone reload."); return; }
                Hash = Text.RightChop(15);
            }
        }
        const auto* ExpectedLevel = BaselineLevels.Find(Id);
        const auto* Row = History.Find(Id);
        const auto* Baseline = History.GetBaselineObjects().FindByPredicate([Id](const auto& Value) { return Value.Id == Id; });
        const auto* Template = Templates.Find(Id);
        const auto* MeshActor = Cast<AStaticMeshActor>(Actor);
        const UStaticMesh* Mesh = MeshActor ? MeshActor->GetStaticMeshComponent()->GetStaticMesh().Get() : nullptr;
        if (!ExpectedLevel || *ExpectedLevel != Package || !Row || !Baseline || !Template || !Mesh || Rebound.Contains(Id)
            || Hash.Len() != 64 || Row->SourceIdentity != Mesh->GetPathName() + TEXT(":") + Hash)
        { StreamingConflict = TEXT("Authored GM models changed during zone reload; draft and undo history were preserved."); return; }
        const auto* Component = MeshActor->GetStaticMeshComponent();
        bool bMatches = Actor->GetActorTransform().Equals(Baseline->Transform, .0001) && Actor->IsHidden() == Baseline->bHidden
            && Component->GetCollisionProfileName() == Template->MeshCollisionProfile
            && Component->GetNumMaterials() == Template->Materials.Num();
        for (int32 Index = 0; bMatches && Index < Template->Materials.Num(); ++Index)
            bMatches &= FSoftObjectPath(Component->GetMaterial(Index)) == Template->Materials[Index].ToSoftObjectPath();
        TArray<UBoxComponent*> Boxes; Actor->GetComponents(Boxes);
        bMatches &= Boxes.Num() == Template->Collision.Num();
        for (const auto& Box : Template->Collision)
        {
            const auto* Found = Boxes.FindByPredicate([&](const auto* Value) { return Value->GetFName() == Box.Name; });
            bMatches &= Found && (*Found)->GetRelativeTransform().Equals(Box.Transform, .0001)
                && (*Found)->GetUnscaledBoxExtent().Equals(Box.Extent, .0001) && (*Found)->GetCollisionProfileName() == Box.Profile;
        }
        if (!bMatches)
        { StreamingConflict = TEXT("Authored GM placement, materials or collision changed during zone reload; the draft was not applied."); return; }
        Rebound.Add(Id, Actor);
    }
    for (const auto& Pair : BaselineLevels)
        if (Pair.Value == Package && !Rebound.Contains(Pair.Key))
        { StreamingConflict = TEXT("An authored GM object is missing after zone reload; draft and undo history were preserved."); return; }
    Actors.Append(Rebound);
    // Recreate only document-owned additions; original actors retain their saved identity and collision.
    FString Error;
    if (!ApplyHistory(History, Error)) StreamingConflict = Error;
}
void UWarWorldEditSubsystem::Deinitialize()
{
    FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
    FWorldDelegates::LevelRemovedFromWorld.Remove(LevelRemovedHandle);
    Actors.Empty(); Templates.Empty(); BaselineLevels.Empty();
    Super::Deinitialize();
}
