#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
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
    void ToggleInventory();
    void ToggleQuestLog();
    void InteractWithStation();
    void InteractWithWorld();
private:
    UPROPERTY(Transient) TObjectPtr<UWarInventoryWidget> InventoryWidget;
    UPROPERTY(Transient) TObjectPtr<UWarQuestLogWidget> QuestLogWidget;
    UPROPERTY(Transient) TObjectPtr<UWarEntryStatusWidget> EntryStatus;
    UPROPERTY(Transient) FText LastEntryFailure;
};
