#include "WarPlayerController.h"
#include "WarWorldEditWidget.h"
#include "WarWorldEditSubsystem.h"
#include "WarInventoryWidget.h"
#include "WarQuestLogWidget.h"
#include "WarCharacter.h"
#include "Engine/World.h"

void AWarPlayerController::PickWorldEditorObject()
{
    if (!WorldEditWidget || !WorldEditWidget->IsInViewport()) return;
    const auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    FVector Origin, Direction;
    if (!Editor || !Editor->CanUse(this) || !DeprojectMousePositionToWorld(Origin, Direction)) return;
    const FName Id = Editor->PickObject(this, Origin, Direction);
    if (Id.IsNone()) { WorldEditMessage = TEXT("No editable building under the pointer. Existing selection retained."); return; }
    WorldEditWidget->SelectObject(Id);
    WorldEditMessage = TEXT("Building selected. Use the controls to edit it.");
}

void AWarPlayerController::ToggleWorldEditor()
{
    if (!IsLocalController() || !GetLocalPlayer() || !LastEntryFailure.IsEmpty()) return;
    if (WorldEditWidget && WorldEditWidget->IsInViewport())
    {
        WorldEditWidget->RemoveFromParent(); SetInputMode(FInputModeGameOnly());
        SetIgnoreLookInput(false); SetIgnoreMoveInput(false); bShowMouseCursor = false; return;
    }
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    FString Error;
    if (!Editor || !Editor->Open(this, Error)) { WorldEditMessage = Error; return; }
    if (InventoryWidget && InventoryWidget->IsInViewport()) ToggleInventory();
    if (QuestLogWidget && QuestLogWidget->IsInViewport()) ToggleQuestLog();
    if (!WorldEditWidget)
    {
        WorldEditWidget = CreateWidget<UWarWorldEditWidget>(this, UWarWorldEditWidget::StaticClass());
        if (WorldEditWidget) WorldEditWidget->SetDesiredSizeInViewport(FVector2D(560, 960));
    }
    if (!WorldEditWidget) return;
    WorldEditWidget->AddToViewport(10);
    WorldEditWidget->SetPositionInViewport(FVector2D(24, 24));
    SetInputMode(FInputModeGameAndUI()); SetIgnoreLookInput(true); SetIgnoreMoveInput(true); bShowMouseCursor = true;
    WorldEditMessage = TEXT("Editing a development draft. Save before leaving the map.");
}

void AWarPlayerController::ServerEditWorldObject_Implementation(FName Id, FTransform Transform, bool bObjectHidden, int32 ExpectedRevision)
{
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error;
    const bool bSuccess = Editor && Editor->Edit(this, Id, Transform, bObjectHidden, ExpectedRevision, Error);
    ClientWorldEditResult(bSuccess ? TEXT("World edit applied.") : (Error.IsEmpty() ? TEXT("GM access unavailable.") : Error));
}

void AWarPlayerController::ServerWorldEditHistory_Implementation(bool bRedo, int32 ExpectedRevision)
{
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error;
    const bool bSuccess = Editor && Editor->Undo(this, bRedo, ExpectedRevision, Error);
    ClientWorldEditResult(bSuccess ? (bRedo ? TEXT("Edit redone.") : TEXT("Edit undone.")) : (Error.IsEmpty() ? TEXT("GM access unavailable.") : Error));
}

void AWarPlayerController::ServerWorldEditDraft_Implementation(bool bLoad, int32 ExpectedRevision)
{
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error;
    const bool bSuccess = Editor && (bLoad ? Editor->LoadDraft(this, ExpectedRevision, Error) : Editor->SaveDraft(this, ExpectedRevision, Error));
    const FString Loaded = bSuccess && bLoad && Editor->GetHistory().GetLoadedBaselineAdditions() > 0
        ? FString::Printf(TEXT("Draft loaded; %d newly imported objects retained. Undo restores previous edits."), Editor->GetHistory().GetLoadedBaselineAdditions())
        : TEXT("Saved draft loaded. Undo restores your previous edits.");
    ClientWorldEditResult(bSuccess ? (bLoad ? Loaded : FString(TEXT("Draft saved locally.")))
        : (Error.IsEmpty() ? TEXT("GM access unavailable.") : Error));
}

void AWarPlayerController::ClientWorldEditResult_Implementation(const FString& Message) { WorldEditMessage = Message; }

void AWarPlayerController::ServerSetDevelopmentTraversal_Implementation(bool bFlying, float SpeedMultiplier)
{
    auto* WarPawn = Cast<AWarCharacter>(GetPawn()); FString Error;
    const bool bSuccess = WarPawn && WarPawn->SetDevelopmentTraversal(bFlying, SpeedMultiplier, Error);
    ClientWorldEditResult(bSuccess ? (bFlying ? TEXT("Flight enabled. Close the panel; E moves up and Q moves down.") : TEXT("Walking enabled."))
        : TEXT("Traversal rejected: ") + (Error.IsEmpty() ? FString(TEXT("Character unavailable.")) : Error));
}

void AWarPlayerController::ServerReturnToDevelopmentSpawn_Implementation()
{
    auto* WarPawn = Cast<AWarCharacter>(GetPawn()); FString Error;
    const bool bSuccess = WarPawn && WarPawn->ReturnToDevelopmentSpawn(Error);
    ClientWorldEditResult(bSuccess ? FString(TEXT("Returned to the capital arrival."))
        : TEXT("Return rejected: ") + (Error.IsEmpty() ? FString(TEXT("Character unavailable.")) : Error));
}

void AWarPlayerController::ServerCreateWorldObject_Implementation(FName TemplateId, FTransform Transform, int32 ExpectedRevision)
{
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error; FName Id;
    const bool bSuccess = Editor && Editor->Create(this, TemplateId, Transform, ExpectedRevision, Id, Error);
    if (bSuccess) ClientWorldObjectCreated(Id);
    ClientWorldEditResult(bSuccess ? TEXT("Building placed. Adjust its position, then save the draft.")
        : TEXT("Creation rejected: ") + (Error.IsEmpty() ? FString(TEXT("GM access unavailable.")) : Error));
}

void AWarPlayerController::ClientWorldObjectCreated_Implementation(FName Id)
{
    if (WorldEditWidget) WorldEditWidget->SelectObject(Id);
}

void AWarPlayerController::ServerPlaceWorldObject_Implementation(FName TemplateId, double Grid, double Angle, int32 ExpectedRevision)
{
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error; FName Id;
    const bool bSuccess = Editor && Editor->CreateInFront(this, TemplateId, Grid, Angle, ExpectedRevision, Id, Error);
    if (bSuccess) ClientWorldObjectCreated(Id);
    ClientWorldEditResult(bSuccess ? TEXT("Model placed on the surface. Adjust it, then save the draft.")
        : TEXT("Placement rejected: ") + (Error.IsEmpty() ? FString(TEXT("GM access unavailable.")) : Error));
}

void AWarPlayerController::ServerDropWorldObject_Implementation(FName Id, int32 ExpectedRevision)
{
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error;
    const bool bSuccess = Editor && Editor->DropToSurface(this, Id, ExpectedRevision, Error);
    ClientWorldEditResult(bSuccess ? TEXT("Model dropped to the surface. Undo restores its previous height.")
        : TEXT("Drop rejected: ") + (Error.IsEmpty() ? FString(TEXT("GM access unavailable.")) : Error));
}
