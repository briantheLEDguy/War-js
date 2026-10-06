#include "WarCombatNetworkProof.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCombatFeedback.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "EngineUtils.h"

void UWarCombatNetworkProof::TickUi(double Now)
{
    if (Now-Started>90) { Finish(false,FString::Printf(TEXT("Combat UI network timeout: observed %d/15"),UiObserved)); return; }
    if (GetWorld()->GetNetMode()==NM_DedicatedServer)
    {
        AWarPlayerController* PC=nullptr;
        for (TActorIterator<AWarPlayerController> It(GetWorld());It;++It) if (It->GetNetConnection()) { PC=*It; break; }
        if (!PC || !PC->GetPlayerState<AWarPlayerState>()) return;
        if (!Actor.IsValid())
        {
            const auto Spawn=[&](const TCHAR* Profile,FVector Position,AController* Controller) {
                auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*(FString(TEXT("/Game/MigrationProof/Visual_"))+Profile));
                if (!Visual) return static_cast<AWarCharacter*>(nullptr);
                FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
                auto* Pawn=GetWorld()->SpawnActor<AWarCharacter>(Position,FRotator::ZeroRotator,Params); Controller->Possess(Pawn);
                auto* State=Controller->GetPlayerState<AWarPlayerState>();
                if (!State) { State=GetWorld()->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State); }
                State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital")); FString Error;
                if (!Pawn->SetVisualDefinition(Visual,Error)) { Finish(false,Error); return static_cast<AWarCharacter*>(nullptr); }
                State->InitializeForPawn(Pawn); Pawn->GetCharacterMovement()->DisableMovement();
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),1000);
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),800);
                Pawn->bAlwaysRelevant=true; Pawn->ForceNetUpdate(); return Pawn;
            };
            if (APawn* Old=PC->GetPawn()) { PC->UnPossess(); Old->Destroy(); }
            Actor=Spawn(TEXT("civic_ember_arcanist_m"),FVector(0,0,3000),PC);
            Target=Spawn(TEXT("mire_warbrute_m"),FVector(500,0,3000),GetWorld()->SpawnActor<AAIController>());
            Friendly=Spawn(TEXT("civic_battle_prelate_m"),FVector(500,300,3000),GetWorld()->SpawnActor<AAIController>());
            if (!Actor.IsValid() || !Target.IsValid() || !Friendly.IsValid()) { Finish(false,TEXT("Missing network model fixtures")); return; }
            ActionAt=Now; return;
        }
        if (Now-ActionAt<(Phase==0?15:.2)) return;
        if (Phase<10)
        {
            WarCombatFeedback::Emit(Actor.Get(),Target.Get(),TEXT("Hit"),11);
            WarCombatFeedback::Emit(Actor.Get(),Friendly.Get(),TEXT("Heal"),22);
            WarCombatFeedback::Emit(Actor.Get(),Actor.Get(),TEXT("Heal"),33);
            Target->SetActorLocation(FVector(500,40,3000));
            Friendly->GetPlayerState<AWarPlayerState>()->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),822);
            Target->GetPlayerState<AWarPlayerState>()->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),789);
        }
        else
        {
            // Explicitly unmapped recipient exercises wire metadata independently of actor resolution.
            // Repeat both phases to tolerate the proof's intentional unreliable packet loss.
            PC->ClientCombatNotice(100000+Phase,TEXT("Heal"),TEXT("Unmapped friendly"),44,400000,nullptr,FVector(500,300,3200),false);
        }
        ActionAt=Now;
        if (++Phase>=20) Finish(true,TEXT("Owner feedback sent for enemy NPC, allied NPC, self and unmapped friendly; health/movement replicated"));
        return;
    }
    if (GetWorld()->GetNetMode()!=NM_Client) return;
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()); if (!PC) return;
    for (const auto& N:PC->GetFloatingCombatNumbers())
    {
        if (N.Amount==11 && N.bEnemy && N.Recipient.IsValid()) UiObserved|=1;
        if (N.Amount==22 && !N.bEnemy && N.Recipient.IsValid()) UiObserved|=2;
        if (N.Amount==33 && !N.bEnemy && N.Recipient==PC->GetPawn()) UiObserved|=4;
        if (N.Amount==44 && !N.bEnemy && !N.Recipient.IsValid()) UiObserved|=8;
    }
    bool Healed=false,Damaged=false,Moved=false;
    for (TActorIterator<AWarCharacter> It(GetWorld());It;++It)
    {
        const auto* State=It->GetPlayerState<AWarPlayerState>(); if (!State) continue;
        if (It->GetAnimationProfile()==TEXT("civic_battle_prelate_m")) Healed=State->GetAttributes()->GetHealth()==822;
        if (It->GetAnimationProfile()==TEXT("mire_warbrute_m")) { Damaged=State->GetAttributes()->GetHealth()==789; Moved=It->GetActorLocation().Y>30; }
    }
    if (UiObserved==15 && Healed && Damaged && Moved) Finish(true,TEXT("Owner/client metadata, self-healing, unmapped friendly styling and replicated NPC health/movement verified"));
}
