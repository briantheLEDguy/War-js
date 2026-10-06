#include "WarPlayerController.h"
#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeLobbyWidget.h"
#include "WarScenarioSession.h"
#include "WarPlayerState.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarSiegeNavigation.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"

void AWarPlayerController::ServerSiegeReady_Implementation(int32 Round, bool Ready)
{
    FString Error;
    auto* Mode = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>();
    if (!Mode || !Mode->SetReady(this, Round, Ready, Error)) ClientWorldEditResult(Error.IsEmpty() ? TEXT("No development siege is available.") : Error);
    else ClientWorldEditResult(TEXT(""));
}
void AWarPlayerController::ServerSiegeSelectRole_Implementation(int32 Round, uint8 CombatRole)
{
    FString Error;
    auto* Mode = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>();
    if (!Mode || !Mode->SelectRole(this, Round, EWarSiegeRole(CombatRole), Error)) ClientWorldEditResult(Error.IsEmpty() ? TEXT("No development siege is available.") : Error);
    else ClientWorldEditResult(TEXT(""));
}
void AWarPlayerController::TickSiegeLobby()
{
    const auto* PS = GetPlayerState<AWarPlayerState>();
    const auto* GS = PS ? PS->GetSiegeEncounter() : nullptr;
    // Preparation precedes membership, but only isolated scenario worlds own this lobby.
    if (!GS && GetWorld()->GetGameState<AWarSiegeGameState>()) GS = AWarSiegeEncounter::Find(GetWorld());
    const bool Open = GS && GS->bDevelopmentLobby && !GS->bQueuedScenario
        && (GS->Siege.Phase == EWarSiegePhase::Waiting || GS->Siege.Phase == EWarSiegePhase::Finished);
    if (Open == bSiegeLobbyInput) return;
    if (Open)
    {
        CloseAllPanels();
        SiegeLobbyWidget = CreateWidget<UWarSiegeLobbyWidget>(this);
        if (!SiegeLobbyWidget) return;
        SiegeLobbyWidget->AddToViewport(50);
        SetInputMode(FInputModeUIOnly().SetWidgetToFocus(SiegeLobbyWidget->TakeWidget()));
        SetIgnoreMoveInput(true); SetIgnoreLookInput(true); bShowMouseCursor = true;
        UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_LOBBY_READY round=%d"), GS->RoundId);
    }
    else
    {
        if (SiegeLobbyWidget) SiegeLobbyWidget->RemoveFromParent();
        SiegeLobbyWidget = nullptr;
        SetIgnoreMoveInput(false); SetIgnoreLookInput(false); bShowMouseCursor = true;
        RestoreGameplayInput();
    }
    bSiegeLobbyInput = Open;
}
void AWarPlayerController::WarSiegeStart(int32 Capacity, int32 Seed) { ServerGmSiegeStart(Capacity, Seed); }
void AWarPlayerController::WarSiegeReset() { ServerGmSiegeReset(); }
void AWarPlayerController::ServerGmSiegeStart_Implementation(int32 Capacity, int32 Seed)
{
    FString Error;
    auto* Mode = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>();
    if (!Mode) Error = TEXT("Open the isolated Aegis siege map before launching a siege.");
    else if (Mode->Launch(this, Capacity, Seed, Error)) Error = TEXT("Bastion siege launched.");
    ClientWorldEditResult(Error);
}
void AWarPlayerController::ServerGmSiegeReset_Implementation()
{
    FString Error;
    auto* Mode = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>();
    if (!Mode) Error = TEXT("No siege is loaded.");
    else if (Mode->ResetSiege(this, Error)) Error = TEXT("Siege reset.");
    ClientWorldEditResult(Error);
}

void AWarPlayerController::ServerSiegeSquadOrder_Implementation(int32 Round,uint8 Order)
{
    auto* Mode=AWarSiegeEncounter::For(this);
    const auto* OrderPawn=Cast<AWarCharacter>(GetPawn());
    if (!Mode || !OrderPawn || OrderPawn->IsDead() || !Mode->IsParticipant(OrderPawn) || !Mode->SiegeState()
        || Mode->SiegeState()->RoundId!=Round || Mode->SiegeState()->Siege.Phase!=EWarSiegePhase::Active
        || Order>3 || (Order==3 && Mode->SiegeState()->Siege.bOptionalComplete)) return;
    if (Order==2)
    {
        // The server movement floor already validates this capsule's walkable
        // position. A path to an arbitrary offset can incorrectly reject Hold.
        if (!OrderPawn->GetCharacterMovement()->IsMovingOnGround())
        { ClientWorldEditResult(TEXT("Hold requires a clear position on walkable ground."));return; }
        SiegeHoldPosition=OrderPawn->GetActorLocation();
    }
    SiegeSquadOrder=Order;
    ClientSiegeSquadState(Order,SiegeSquadCount);
}
void AWarPlayerController::ClientSiegeSquadState_Implementation(uint8 Order,int32 Count)
{ SiegeSquadOrder=Order; SiegeSquadCount=Count; }

void AWarPlayerController::ServerPrepareScenario_Implementation()
{ GetGameInstance()->GetSubsystem<UWarScenarioSession>()->RegisterAuthority(this); }
void AWarPlayerController::ClientScenarioConnectionStatus_Implementation(bool Pending,const FString& Message)
{ GetGameInstance()->GetSubsystem<UWarScenarioSession>()->SetConnectionStatus(Pending,Message); }
void AWarPlayerController::ServerScenarioDepart_Implementation(const FString& Ticket)
{ GetGameInstance()->GetSubsystem<UWarScenarioSession>()->RegisterAuthority(this,Ticket); }
void AWarPlayerController::ClientScenarioRegistered_Implementation(const FString& Url,const FString& Token,const FString& Id)
{ ScenarioCharacterId=Id;GetGameInstance()->GetSubsystem<UWarScenarioSession>()->SetCredentials(Url,Token,Id); }
void AWarPlayerController::ClientScenarioTravel_Implementation(const FString& Endpoint,const FString& Ticket)
{ GetGameInstance()->GetSubsystem<UWarScenarioSession>()->Travel(Endpoint,Ticket); }

void AWarPlayerController::ServerCampaignSiegeEnrollment_Implementation(bool Join)
{ if (auto* Bridge = GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>()) Bridge->Enroll(this, Join); }
void AWarPlayerController::WarCampaignSiegeJoin() { ServerCampaignSiegeEnrollment(true); }
void AWarPlayerController::WarCampaignSiegeLeave() { ServerCampaignSiegeEnrollment(false); }
