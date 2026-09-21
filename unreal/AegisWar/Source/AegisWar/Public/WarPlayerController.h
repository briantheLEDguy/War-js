#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "WarCameraRules.h"
#include "WarPlayerController.generated.h"

class UWarEntryStatusWidget;
class UWarInventoryWidget;
class UWarQuestLogWidget;
class UWarWorldEditWidget;

UCLASS()
class AEGISWAR_API AWarPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    UFUNCTION(Client, Reliable) void ClientEntryRejected(const FText& Reason);
    void RecordEntryFailure(const FText& Reason);
    const FText& GetEntryFailure() const { return LastEntryFailure; }
    virtual void SetupInputComponent() override;
    virtual void UpdateRotation(float DeltaTime) override;
    void ToggleInventory();
    void ToggleQuestLog();
    void ToggleWorldEditor();
    void PickWorldEditorObject();
    UFUNCTION(Server, Reliable) void ServerSetDevelopmentTraversal(bool bFlying, float SpeedMultiplier);
    UFUNCTION(Server, Reliable) void ServerReturnToDevelopmentSpawn();
    UFUNCTION(Server, Reliable) void ServerEditWorldObject(FName Id, FTransform Transform, bool bObjectHidden, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerCreateWorldObject(FName TemplateId, FTransform Transform, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerPlaceWorldObject(FName TemplateId, double Grid, double Angle, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerDropWorldObject(FName Id, int32 ExpectedRevision);
    UFUNCTION(Client, Reliable) void ClientWorldObjectCreated(FName Id);
    UFUNCTION(Server, Reliable) void ServerWorldEditHistory(bool bRedo, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerWorldEditDraft(bool bLoad, int32 ExpectedRevision);
    UFUNCTION(Client, Reliable) void ClientWorldEditResult(const FString& Message);
    const FString& GetWorldEditMessage() const { return WorldEditMessage; }
    void InteractWithStation();
    void InteractWithWorld();
    /** No-op unless the explicitly opted-in development proof subsystem exists. */
    UFUNCTION(Server, Reliable) void ServerDevelopmentProofReady();
    UFUNCTION(Client, Reliable) void ClientDevelopmentProofStart();
    FWarCameraState& GetLocalCameraState() { return LocalCameraState; }
    void InitializeCameraYaw(double Yaw)
    {
        if (!bCameraInitialized) { LocalCameraState.Yaw = Yaw; bCameraInitialized = true; }
    }
private:
    UPROPERTY(Transient) TObjectPtr<UWarInventoryWidget> InventoryWidget;
    UPROPERTY(Transient) TObjectPtr<UWarQuestLogWidget> QuestLogWidget;
    UPROPERTY(Transient) TObjectPtr<UWarWorldEditWidget> WorldEditWidget;
    FString WorldEditMessage;
    UPROPERTY(Transient) TObjectPtr<UWarEntryStatusWidget> EntryStatus;
    UPROPERTY(Transient) FText LastEntryFailure;
    // The controller survives pawn death; zoom, orbit and preferences must survive it too.
    FWarCameraState LocalCameraState;
    bool bCameraInitialized = false;
};
