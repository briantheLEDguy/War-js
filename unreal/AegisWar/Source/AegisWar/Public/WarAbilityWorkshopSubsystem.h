#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "WarAbilityWorkshopDocument.h"
#include "WarAbilityDeploymentJournal.h"
#include "Tickable.h"
#include "WarAbilityWorkshopSubsystem.generated.h"
class AWarPlayerController;

UCLASS()
class AEGISWAR_API UWarAbilityWorkshopSubsystem : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
    virtual bool IsTickable() const override { return !IsTemplate(); }
    virtual UWorld* GetTickableGameObjectWorld() const override;
    FWarAbilityWorkshopDocument& Document() { return Draft; }
    const FString& GetMessage() const { return Message; }
    const FString& GetEnvironment() const { return Environment; }
    bool SetEnvironment(const FString& Value);
    bool SaveLocal();
    void SaveShared();
    void LoadShared(const FString& WorkspaceId);
    void Publish(const FString& Name);
    void Deploy(const FString& VersionId);
    void RefreshHistory();
    void Retry();
    void Autosave();
    void ResolveConflict(const FString& Path,bool bUseYours);
    void CommitMerge();
    const TArray<FWarWorkshopConflict>& Conflicts() const { return ConflictFields; }
    bool ApplyToDevelopment(AWarPlayerController* Controller);
    bool RollbackPersonal(AWarPlayerController* Controller,const FString& VersionId);
    bool RestoreShipped(AWarPlayerController* Controller);
    bool ValidatePersonal(const TSharedPtr<FJsonObject>& Workspace,FString& Error) const;
    const TArray<TSharedPtr<FJsonValue>>& PersonalHistory() const;
    const FString& DeploymentStatus() const { return PersonalStatus; }
    bool PersonalPending() const { return !PersonalPendingVersion.IsEmpty(); }
    bool ValidatePresentations(const TArray<FWarAbilityDefinition>& Definitions,FString& Error) const;
    TSharedPtr<FJsonObject> ReviewBaseline(FString& Version,FString& Error) const;
    bool IsRequestPending() const { return bRequestPending; }
    uint64 RemoteSerial() const { return RemoteChangeSerial; }
    const TArray<TSharedPtr<FJsonValue>>& History() const { return Versions; }
    const TArray<TSharedPtr<FJsonValue>>& Deployments() const { return DeploymentRows; }
    const TSharedPtr<FJsonObject>& Conflict() const { return ConflictDocument; }
    void SetMessage(const FString& Value) { Message=Value; }
private:
    void Operation(const FString& Action,const TSharedPtr<FJsonObject>& Body);
    void SendPending();
    FWarAbilityWorkshopDocument Draft;
    FString Message,Environment=TEXT("development"),LastSaved,PendingRequest,PendingAction;
    uint64 PendingSerial=0;
    uint64 SharedSerial=MAX_uint64;
    uint64 RemoteChangeSerial=0;
    bool bSharedAutosave=false;
    bool bRequestPending=false;
    TArray<TSharedPtr<FJsonValue>> Versions,DeploymentRows;
    TSharedPtr<FJsonObject> ConflictDocument;
    TSharedPtr<FJsonObject> SharedBaseline,MergePreview;
    TArray<FWarWorkshopConflict> ConflictFields;
    TMap<FString,bool> ConflictChoices;
    void BuildMerge();
    TUniquePtr<FWarAbilityDeploymentJournal> PersonalJournal;
    FString PersonalPendingVersion,PersonalStatus;
    bool bRestoreChecked=false,bRestoringPersonal=false;
    double PersonalDeadline=0;
    bool EnsurePersonal(AWarPlayerController* Controller);
    bool StagePersonal(const TSharedPtr<FJsonObject>& Workspace,const FString& Version);
    FString PersonalDirectory() const;
};
