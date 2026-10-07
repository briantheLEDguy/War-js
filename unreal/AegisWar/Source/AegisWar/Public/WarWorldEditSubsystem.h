#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarWorldEditHistory.h"
#include "WarWorldEditPracticalLights.h"
#include "WarWorldEditSubsystem.generated.h"

class APlayerController;

/** Development capital workbench. Production and remote GM authorization remain closed. */
UCLASS()
class AEGISWAR_API UWarWorldEditSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    bool CanUse(const APlayerController* Controller) const;
    bool Open(APlayerController* Controller, FString& Error);
    bool Create(APlayerController* Controller, FName TemplateId, const FTransform& Transform, int32 Revision, FName& CreatedId, FString& Error);
    bool CreateInFront(APlayerController* Controller, FName TemplateId, double Grid, double Angle, int32 Revision, FName& CreatedId, FString& Error);
    bool DropToSurface(APlayerController* Controller, FName Id, int32 Revision, FString& Error);
    bool CreateRow(APlayerController* Controller, FName Id, int32 Count, bool bAlongY, double Gap, double Grid, int32 Revision, FName& CreatedId, FString& Error);
    bool Edit(APlayerController* Controller, FName Id, const FTransform& Transform, bool bHidden, int32 Revision, FString& Error);
    bool Undo(APlayerController* Controller, bool bRedo, int32 Revision, FString& Error);
    bool ResetDraft(APlayerController* Controller, int32 Revision, FString& Error);
    bool Duplicate(APlayerController* Controller, FName Id, int32 Revision, FName& CreatedId, FString& Error);
    bool SaveDraft(APlayerController* Controller, int32 Revision, FString& Error);
    bool LoadDraft(APlayerController* Controller, int32 Revision, FString& Error);
    bool Publish(APlayerController* Controller, int32 Revision, FString& Error);
    void SyncRemote(APlayerController* Controller, bool bPublish);
    FString GetRemoteStatus() const { return RemoteStatus; }
    class UStaticMesh* GetTemplateMesh(FName Id) const;
    bool ResolvePlacement(APlayerController* Controller, FName TemplateId, FVector Origin, FVector Direction,
        double Grid, double Angle, FTransform& Transform, FString& Error);
    const FWarWorldEditHistory& GetHistory() const { return History; }
    AActor* GetObjectActor(FName Id) const;
    FName PickObject(const APlayerController* Controller, FVector Origin, FVector Direction) const;
    FString GetDraftLocation() const;
    FString GetPublicationLocation() const;
    const FString& GetPublicationLoadError() const { return PublicationLoadError; }
private:
    friend class FWarWorldEditStreamingTest;
    friend class FWarWorldEditPracticalLightTest;
    bool Ready(APlayerController* Controller, FString& Error);
    bool ApplyHistory(FWarWorldEditHistory Next, FString& Error);
    void ApplyActors();
    void LevelAdded(class ULevel* Level, UWorld* World);
    void LevelRemoved(class ULevel* Level, UWorld* World);
    class ULevel* LoadedLevel(FName Package) const;
    FDelegateHandle LevelAddedHandle, LevelRemovedHandle;
    TMap<FName, FName> BaselineLevels;
    FString StreamingConflict;
    bool bInitialized = false;
    struct FCollisionTemplate
    {
        FTransform Transform;
        FVector Extent;
        FName Profile;
        FName Name;
    };
    struct FModelTemplate
    {
        TSoftObjectPtr<class UStaticMesh> Mesh;
        FName LevelPackage;
        FName MeshCollisionProfile = TEXT("NoCollision");
        TArray<TSoftObjectPtr<class UMaterialInterface>> Materials;
        TArray<FCollisionTemplate> Collision;
        TArray<FWarWorldEditPracticalLight> PracticalLights;
    };
    TMap<FName, FModelTemplate> Templates;
    FWarWorldEditHistory History;
    TMap<FName, TWeakObjectPtr<AActor>> Actors;
    FString LastDiskContents;
    bool bObservedDisk = false;
    FString LastPublishedContents;
    FString PublicationLoadError;
    bool bRemoteBusy = false;
    int32 RemoteRevision = INDEX_NONE;
    FString RemoteScope, PendingRemoteRequest;
    FString RemoteStatus = TEXT("Remote world: not synced. Developer sign-in and a configured gateway are required.");
};
