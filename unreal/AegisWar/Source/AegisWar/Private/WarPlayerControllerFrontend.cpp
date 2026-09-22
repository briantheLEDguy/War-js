#include "WarPlayerController.h"
#include "WarFrontendWidget.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "WarRuntimeSettings.h"
#include "WarPlayerState.h"
#include "WarGameMode.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

void AWarPlayerController::ClientOpenFrontend_Implementation()
{
    if (!IsLocalController() || !GetLocalPlayer()) return;
    if (!FrontendWidget) FrontendWidget = CreateWidget<UWarFrontendWidget>(this, UWarFrontendWidget::StaticClass());
    if (!FrontendWidget) return;
    if (!FrontendWidget->IsInViewport()) FrontendWidget->AddToViewport(200);
    FInputModeUIOnly Input;
    Input.SetWidgetToFocus(FrontendWidget->TakeWidget());
    SetInputMode(Input);
    bShowMouseCursor = true;
}

void AWarPlayerController::ClientCharacterEntryResult_Implementation(bool bAccepted, const FString& Error)
{
    if (!bAccepted)
    {
        if (FrontendWidget) FrontendWidget->ShowError(Error);
        return;
    }
    if (FrontendWidget) FrontendWidget->RemoveFromParent();
    LastEntryFailure = FText::GetEmpty();
    ResetIgnoreMoveInput(); ResetIgnoreLookInput();
    if (IsLocalController() && GetLocalPlayer()) SetInputMode(FInputModeGameOnly());
    bShowMouseCursor = false;
}

void AWarPlayerController::BeginCharacterEntry(UWarCharacterVisualDefinition* Visual)
{
    if (!HasAuthority() || bCharacterEntryPending || GetPawn() || !Visual) return;
    CreatedCharacterVisual = Visual;
    LastEntryFailure = FText::GetEmpty();
    bCharacterEntryPending = true;
    if (FrontendWidget) FrontendWidget->ShowError(TEXT("Loading starting city..."));
}

void AWarPlayerController::CompleteCharacterEntry()
{
    if (!HasAuthority() || !bCharacterEntryPending || !IsValid(GetPawn()) || GetPawn()->GetController() != this) return;
    bCharacterEntryPending = false;
    ClientCharacterEntryResult(true, FString());
}

void AWarPlayerController::ServerCreateDevelopmentCharacter_Implementation(const FString& Name, FName Race, FName Career, FName Body)
{
    // This is a local editor/development fixture, never a production authentication bypass.
    if (UE_BUILD_SHIPPING || GetNetMode() != NM_Standalone)
    { ClientCharacterEntryResult(false, TEXT("Character creation requires a local Development session. Online accounts are not connected yet.")); return; }
    if (bCharacterEntryPending) return;
    // Repeated submission after possession resumes the existing session.
    if (GetPawn()) { ClientCharacterEntryResult(true, FString()); return; }
    FString Error;
    if (!UWarFrontendWidget::ValidateCharacterName(Name, Error)) { ClientCharacterEntryResult(false, Error); return; }
    const auto* Settings = GetDefault<UWarRuntimeSettings>();
    auto* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    auto* State = GetPlayerState<AWarPlayerState>();
    auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>();
    if (!Content || !Content->IsContentReady() || !State || !Mode)
    { ClientCharacterEntryResult(false, TEXT("Character content is not ready. Check the migration content installation and retry.")); return; }
    UWarCharacterVisualDefinition* Visual = nullptr;
    for (const auto& Candidate : {Settings->AegisDevelopmentVisual, Settings->RiftboundDevelopmentVisual})
    {
        auto* Loaded = Candidate.LoadSynchronous();
        if (Loaded && Loaded->RaceId == Race && Loaded->ClassId == Career && Loaded->BodyVariant == Body) { Visual = Loaded; break; }
    }
    if (!Visual)
    { ClientCharacterEntryResult(false, TEXT("This race, career and body do not have a configured native model yet. Edit your character or retry after its model is imported. The current Aegis development option is Empire / Battle Prelate / Male.")); return; }
    if (!Visual->ValidateForSpawn(Visual->Realm, Error) || !Content->ValidatePlayableVisual(Visual, Error))
    { ClientCharacterEntryResult(false, Error); return; }
    // The current startup world is the Aegis capital. Never place an enemy-realm draft in it.
    if (Visual->Realm != EWarRealm::Aegis)
    { ClientCharacterEntryResult(false, TEXT("Riftspire Citadel entry is not available yet. Your Riftbound character cannot enter the Aegis capital.")); return; }
    if (State->GetRealm() != EWarRealm::None && State->GetRealm() != Visual->Realm)
    { ClientCharacterEntryResult(false, TEXT("The session realm does not match this character.")); return; }
    State->SetDevelopmentRealm(Visual->Realm);
    State->SetPlayerName(Name);
    BeginCharacterEntry(Visual);
    // Zone streaming can defer RestartPlayer; the game mode reports possession or a real failure.
    Mode->RestartPlayer(this);
}
