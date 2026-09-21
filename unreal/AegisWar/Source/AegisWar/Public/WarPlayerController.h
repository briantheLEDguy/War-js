#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "WarCameraRules.h"
#include "WarPlayerController.generated.h"

class UWarEntryStatusWidget;
class UWarInventoryWidget;
class UWarQuestLogWidget;

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
    void InteractWithStation();
    void InteractWithWorld();
    FWarCameraState& GetLocalCameraState() { return LocalCameraState; }
    void InitializeCameraYaw(double Yaw)
    {
        if (!bCameraInitialized) { LocalCameraState.Yaw = Yaw; bCameraInitialized = true; }
    }
private:
    UPROPERTY(Transient) TObjectPtr<UWarInventoryWidget> InventoryWidget;
    UPROPERTY(Transient) TObjectPtr<UWarQuestLogWidget> QuestLogWidget;
    UPROPERTY(Transient) TObjectPtr<UWarEntryStatusWidget> EntryStatus;
    UPROPERTY(Transient) FText LastEntryFailure;
    // The controller survives pawn death; zoom, orbit and preferences must survive it too.
    FWarCameraState LocalCameraState;
    bool bCameraInitialized = false;
};
