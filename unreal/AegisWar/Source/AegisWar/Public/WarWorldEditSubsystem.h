#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarWorldEditHistory.h"
#include "WarWorldEditSubsystem.generated.h"

class APlayerController;

/** Development capital workbench. Production and remote GM authorization remain closed. */
UCLASS()
class AEGISWAR_API UWarWorldEditSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    bool CanUse(const APlayerController* Controller) const;
    bool Open(APlayerController* Controller, FString& Error);
    bool Create(APlayerController* Controller, FName TemplateId, const FTransform& Transform, int32 Revision, FName& CreatedId, FString& Error);
    bool CreateInFront(APlayerController* Controller, FName TemplateId, double Grid, double Angle, int32 Revision, FName& CreatedId, FString& Error);
    bool DropToSurface(APlayerController* Controller, FName Id, int32 Revision, FString& Error);
    bool Edit(APlayerController* Controller, FName Id, const FTransform& Transform, bool bHidden, int32 Revision, FString& Error);
    bool Undo(APlayerController* Controller, bool bRedo, int32 Revision, FString& Error);
    bool SaveDraft(APlayerController* Controller, int32 Revision, FString& Error);
    bool LoadDraft(APlayerController* Controller, int32 Revision, FString& Error);
    const FWarWorldEditHistory& GetHistory() const { return History; }
    AActor* GetObjectActor(FName Id) const;
    FName PickObject(const APlayerController* Controller, FVector Origin, FVector Direction) const;
    FString GetDraftLocation() const;
private:
    bool Ready(APlayerController* Controller, FString& Error);
    bool ApplyHistory(FWarWorldEditHistory Next, FString& Error);
    void ApplyActors();
    struct FCollisionTemplate
    {
        FTransform Transform;
        FVector Extent;
        FName Profile;
        FName Name;
    };
    struct FModelTemplate
    {
        TWeakObjectPtr<class UStaticMesh> Mesh;
        FName MeshCollisionProfile = TEXT("NoCollision");
        TArray<TWeakObjectPtr<class UMaterialInterface>> Materials;
        TArray<FCollisionTemplate> Collision;
    };
    TMap<FName, FModelTemplate> Templates;
    FWarWorldEditHistory History;
    TMap<FName, TWeakObjectPtr<AActor>> Actors;
    FString LastDiskContents;
    bool bObservedDisk = false;
};
