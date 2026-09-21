#include "WarPlayerController.h"
#include "WarEntryStatusWidget.h"
#include "WarInventoryWidget.h"
#include "WarQuestLogWidget.h"
#include "WarQuestNpc.h"
#include "WarCraftingStation.h"
#include "WarResourceNode.h"
#include "WarPlayerState.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Components/InputComponent.h"
#include "InputCoreTypes.h"

void AWarPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::I, IE_Pressed, this, &AWarPlayerController::ToggleInventory);
    InputComponent->BindKey(EKeys::L, IE_Pressed, this, &AWarPlayerController::ToggleQuestLog);
    InputComponent->BindKey(EKeys::E, IE_Pressed, this, &AWarPlayerController::InteractWithWorld);
}

void AWarPlayerController::ToggleInventory()
{
    if (!IsLocalController() || !GetLocalPlayer() || !LastEntryFailure.IsEmpty()) return;
    if (QuestLogWidget && QuestLogWidget->IsInViewport()) ToggleQuestLog();
    if (InventoryWidget && InventoryWidget->IsInViewport())
    {
        InventoryWidget->RemoveFromParent();
        SetInputMode(FInputModeGameOnly());
        bShowMouseCursor = false;
        SetIgnoreLookInput(false);
        SetIgnoreMoveInput(false);
        return;
    }
    if (!InventoryWidget) InventoryWidget = CreateWidget<UWarInventoryWidget>(this, UWarInventoryWidget::StaticClass());
    if (!InventoryWidget) return;
    InventoryWidget->SetCraftingStation(nullptr);
    InventoryWidget->AddToViewport(10);
    InventoryWidget->SetPositionInViewport(FVector2D(32, 32));
    InventoryWidget->SetDesiredSizeInViewport(FVector2D(540, 650));
    SetInputMode(FInputModeGameAndUI());
    SetIgnoreLookInput(true);
    SetIgnoreMoveInput(true);
    bShowMouseCursor = true;
}

void AWarPlayerController::InteractWithStation()
{
    if (!IsLocalController() || !GetPawn() || !LastEntryFailure.IsEmpty()) return;
    AWarCraftingStation* Nearest = nullptr;
    double Distance = TNumericLimits<double>::Max();
    for (TActorIterator<AWarCraftingStation> It(GetWorld()); It; ++It)
    {
        if (!It->CanInteract(GetPawn())) continue;
        const double Candidate = FVector::DistSquared(GetPawn()->GetActorLocation(), It->GetActorLocation());
        if (Candidate < Distance) { Distance = Candidate; Nearest = *It; }
    }
    if (!Nearest) return;
    if (!InventoryWidget || !InventoryWidget->IsInViewport()) ToggleInventory();
    if (InventoryWidget) InventoryWidget->SetCraftingStation(Nearest);
}

void AWarPlayerController::ToggleQuestLog()
{
    if (!IsLocalController() || !GetLocalPlayer() || !LastEntryFailure.IsEmpty()) return;
    if (QuestLogWidget && QuestLogWidget->IsInViewport())
    {
        QuestLogWidget->RemoveFromParent();
        SetInputMode(FInputModeGameOnly());
        SetIgnoreLookInput(false);
        SetIgnoreMoveInput(false);
        bShowMouseCursor = false;
        return;
    }
    if (InventoryWidget && InventoryWidget->IsInViewport()) ToggleInventory();
    if (!QuestLogWidget) QuestLogWidget = CreateWidget<UWarQuestLogWidget>(this, UWarQuestLogWidget::StaticClass());
    if (!QuestLogWidget) return;
    QuestLogWidget->SetNpc(nullptr);
    QuestLogWidget->AddToViewport(10);
    QuestLogWidget->SetPositionInViewport(FVector2D(32, 32));
    QuestLogWidget->SetDesiredSizeInViewport(FVector2D(540, 650));
    SetInputMode(FInputModeGameAndUI());
    SetIgnoreLookInput(true);
    SetIgnoreMoveInput(true);
    bShowMouseCursor = true;
}

void AWarPlayerController::RecordEntryFailure(const FText& Reason)
{
    if (!HasAuthority()) return;
    LastEntryFailure = Reason;
    ClientEntryRejected(Reason);
}

void AWarPlayerController::ClientEntryRejected_Implementation(const FText& Reason)
{
    LastEntryFailure = Reason;
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    if (!IsLocalController() || !GetLocalPlayer()) return;
    if (!EntryStatus) EntryStatus = CreateWidget<UWarEntryStatusWidget>(this, UWarEntryStatusWidget::StaticClass());
    if (EntryStatus)
    {
        EntryStatus->SetEntryError(Reason);
        if (!EntryStatus->IsInViewport()) EntryStatus->AddToViewport(100);
    }
    SetInputMode(FInputModeUIOnly());
    bShowMouseCursor = true;
}

void AWarPlayerController::InteractWithWorld()
{
    if (QuestLogWidget && QuestLogWidget->IsInViewport()) return;
    if (InventoryWidget && InventoryWidget->IsInViewport()) return;
    if (!IsLocalController() || !GetPawn() || !LastEntryFailure.IsEmpty()) return;
    auto* State = GetPlayerState<AWarPlayerState>();
    if (!State) return;
    AWarQuestNpc* Npc = nullptr;
    double NpcDistance = TNumericLimits<double>::Max();
    for (TActorIterator<AWarQuestNpc> It(GetWorld()); It; ++It)
    {
        FString Name, Error;
        if (!It->ResolveInteraction(GetPawn(), Name, Error)) continue;
        const double Candidate = FVector::DistSquared(GetPawn()->GetActorLocation(), It->GetActorLocation());
        if (Candidate < NpcDistance) { NpcDistance = Candidate; Npc = *It; }
    }
    if (Npc)
    {
        ToggleQuestLog();
        if (QuestLogWidget) QuestLogWidget->SetNpc(Npc);
        return;
    }
    AWarResourceNode* Nearest = nullptr;
    double Distance = TNumericLimits<double>::Max();
    const int64 NowMs = (FDateTime::UtcNow() - FDateTime(1970, 1, 1)).GetTicks() / ETimespan::TicksPerMillisecond;
    for (TActorIterator<AWarResourceNode> It(GetWorld()); It; ++It)
    {
        FWarResourceDefinition Definition; FString Error;
        if (!It->ResolveInteraction(GetPawn(), Definition, Error)
            || !WarGathering::IsAvailable(State->GetInventory(), Definition.ZoneId, Definition.NodeId, NowMs)) continue;
        const double Candidate = FVector::DistSquared2D(GetPawn()->GetActorLocation(), It->GetActorLocation());
        if (Candidate < Distance) { Distance = Candidate; Nearest = *It; }
    }
    if (Nearest) State->ServerGatherResource(Nearest, State->GetInventory().Revision);
    else InteractWithStation();
}
