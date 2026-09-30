#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarAbilityRuntime.h"
#include "WarAttributeSet.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarCombatStatus.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatFluidityTest,"AegisWar.Foundation.CombatFluidity",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCombatFluidityTest::RunTest(const FString& Parameters)
{
    auto* Instance=NewObject<UGameInstance>(GEngine); Instance->AddToRoot(); Instance->InitializeStandalone();
    auto* World=Instance->GetWorld(); World->InitializeActorsForPlay(FURL()); World->BeginPlay(); World->GetWorldSettings()->NotifyBeginPlay();
    auto* Floor=World->SpawnActor<AActor>(); auto* Box=NewObject<UBoxComponent>(Floor); Floor->SetRootComponent(Box);
    Box->SetBoxExtent(FVector(5000,5000,20)); Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Box->SetCollisionObjectType(ECC_WorldStatic); Box->SetCollisionResponseToAllChannels(ECR_Block); Box->RegisterComponent(); Floor->SetActorLocation(FVector(0,0,-20));
    const auto Advance=[&](float Seconds) { for (int I=0;I<FMath::CeilToInt(Seconds*120);++I) { ++GFrameCounter; World->Tick(LEVELTICK_All,1.f/120); } };
    const auto Spawn=[&](const TCHAR* Path,FVector Position) {
        auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,Path);
        if (!TestNotNull(TEXT("Imported test visual"),Visual)) return static_cast<AWarCharacter*>(nullptr);
        auto* Pawn=World->SpawnActor<AWarCharacter>(Position,FRotator::ZeroRotator);
        auto* Controller=World->SpawnActor<AAIController>(); Controller->Possess(Pawn);
        auto* State=World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        FString Error; TestTrue(TEXT("Visual admitted"),Pawn->SetVisualDefinition(Visual,Error));
        State->InitializeForPawn(Pawn); State->SetSiegeNormalized(true); State->GetClassAbilities()->InitializeCharacter(Pawn);
        return Pawn;
    };
    auto* Pawn=Spawn(TEXT("/Game/MigrationProof/Visual_civic_ember_arcanist_m"),FVector(0,0,99));
    auto* Target=Spawn(TEXT("/Game/MigrationProof/Visual_mire_warbrute_m"),FVector(400,0,99));
    if (Pawn && Target)
    {
        auto* State=Pawn->GetPlayerState<AWarPlayerState>(); auto* ASC=State->GetAbilitySystemComponent();
        auto* Runtime=State->GetClassAbilities(); auto* Catalog=Instance->GetSubsystem<UWarAbilityCatalog>();
        const auto Kit=Catalog->Kit(Pawn->GetCareerId());
        if (TestTrue(TEXT("Two real ability presentations available"),Kit.Num()>=2))
        {
            FWarAbilityDefinition Spell=*Kit[0], Followup=*Kit[1];
            for (auto* A : {&Spell,&Followup})
            {
                A->bAuthoredTiming=true; A->TimingMode=TEXT("cast"); A->CastSeconds=.4f; A->bCancelOnMovement=true;
                A->Cooldown=3; A->Gcd=1; A->Mana=10; A->Cost=20; A->Build=5; A->MinimumResource=0; A->ResourceMax=100;
                A->bSpendAll=false; A->UnlockLevel=1; A->Conditions.Reset(); A->Effects.Reset(); A->Shape=TEXT("projectile");
                A->bEnemyTarget=true; A->TargetKind=TEXT("enemy"); A->Range=3000; A->ProjectileSpeed=0;
                FWarAbilityEffect Damage; Damage.Id=TEXT("damage"); Damage.Kind=TEXT("damage"); Damage.Minimum=Damage.Maximum=10; A->Effects.Add(Damage);
            }
            FString Error;
            const auto Install=[&] { TestTrue(TEXT("Install controlled timing fixtures"),Catalog->Install({Spell,Followup},TEXT("fluid-test"),Error)); };
            const auto Reset=[&] {
                Runtime->Interrupt(); Runtime->UpdateMovementIntent(false); Runtime->ResetCooldowns(); Runtime->RestoreResource();
                UWarCombatStatus::On(Pawn)->Clear(); Pawn->GetCharacterMovement()->StopMovementImmediately();
                Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking); Pawn->SetActorLocation(FVector(0,0,99));
                ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxManaAttribute(),1000); ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),100);
                ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),1000);
                Target->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),2000);
                Target->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),2000); Advance(.05f);
            };
            const auto Health=[&] { return Target->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth(); };
            Install(); Reset();
            Runtime->UpdateMovementIntent(true);
            TestFalse(TEXT("Held movement rejects stationary cast"),Runtime->TryActivate(Spell.Id,Target,Error));
            TestEqual(TEXT("Rejected cast costs nothing"),State->GetAttributes()->GetMana(),100.f);
            Runtime->UpdateMovementIntent(false);
            TestTrue(TEXT("Stationary cast starts"),Runtime->TryActivate(Spell.Id,Target,Error));
            ASC->ApplyModToAttribute(UWarAttributeSet::GetManaAttribute(),EGameplayModOp::Additive,-7);
            Runtime->UpdateMovementIntent(true);
            TestEqual(TEXT("Refund preserves unrelated mana spend"),State->GetAttributes()->GetMana(),93.f);
            TestEqual(TEXT("Refund reverses net career cost and build"),Runtime->GetResource(),100.f);
            TestTrue(TEXT("Cancellation retains GCD but removes individual cooldown"),Runtime->Cooldown(Spell.Id)>.8 && Runtime->Cooldown(Spell.Id)<=1);
            Runtime->UpdateMovementIntent(true,true); TestEqual(TEXT("Repeated cancellation cannot refund twice"),State->GetAttributes()->GetMana(),93.f);
            Advance(.6f); TestEqual(TEXT("Cancelled spell cannot hit later"),Health(),2000.f);

            Reset(); Runtime->TryActivate(Spell.Id,Target,Error); Advance(.39f); Runtime->UpdateMovementIntent(true); Advance(.1f);
            TestEqual(TEXT("Cancellation immediately before release prevents impact"),Health(),2000.f);
            TestEqual(TEXT("Cancellation immediately before release refunds cost"),State->GetAttributes()->GetMana(),100.f);
            Reset(); Runtime->TryActivate(Spell.Id,Target,Error); Advance(.41f); Runtime->UpdateMovementIntent(true);
            TestEqual(TEXT("Cancellation immediately after release retains impact"),Health(),1990.f);
            TestEqual(TEXT("Cancellation immediately after release retains cost"),State->GetAttributes()->GetMana(),90.f);

            Reset(); TestTrue(TEXT("Jump-cancel fixture starts"),Runtime->TryActivate(Spell.Id,Target,Error));
            Runtime->UpdateMovementIntent(false,true); TestTrue(TEXT("Jump cancels cast"),Runtime->GetCastingAbility().IsNone());
            Reset(); TestTrue(TEXT("Turning fixture starts"),Runtime->TryActivate(Spell.Id,Target,Error));
            Pawn->SetActorRotation(FRotator(0,45,0)); Advance(.1f); TestEqual(TEXT("Turning preserves spell"),Runtime->GetCastingAbility(),Spell.Id);
            Pawn->ReactToHit(Target,500); TestEqual(TEXT("Heavy hit does not interrupt"),Runtime->GetCastingAbility(),Spell.Id);
            Runtime->Interrupt(); TestTrue(TEXT("Explicit interruption remains available"),Runtime->GetCastingAbility().IsNone());

            Spell.bSpendAll=true; Install(); Reset(); Runtime->TryActivate(Spell.Id,Target,Error); Runtime->UpdateMovementIntent(true);
            TestEqual(TEXT("Spend-all cancellation reverses actual delta"),Runtime->GetResource(),100.f); Spell.bSpendAll=false;
            Spell.ProjectileSpeed=500; Install(); Reset(); Runtime->TryActivate(Spell.Id,Target,Error); Advance(.45f);
            TestFalse(TEXT("Projectile flight is not recovery"),Runtime->IsBusy());
            TestEqual(TEXT("Projectile still in flight"),Health(),2000.f);
            Runtime->UpdateMovementIntent(true); Runtime->ResetCooldowns(); Followup.bCancelOnMovement=false; Install();
            TestTrue(TEXT("Next ability starts during projectile flight"),Runtime->TryActivate(Followup.Id,Target,Error));
            Advance(1); TestEqual(TEXT("Both independent impacts resolve once"),Health(),1980.f);
            TestEqual(TEXT("Released spells retain mana cost"),State->GetAttributes()->GetMana(),80.f);

            Spell.ProjectileSpeed=0; Spell.TimingMode=TEXT("channel"); Spell.ChannelSeconds=1; Spell.TickInterval=.2f; Install(); Reset();
            Runtime->TryActivate(Spell.Id,Target,Error); Advance(.45f); Runtime->UpdateMovementIntent(true); Advance(1);
            TestEqual(TEXT("Movement stops remaining channel ticks"),Health(),1990.f);
            TestEqual(TEXT("Partial channel keeps cost"),State->GetAttributes()->GetMana(),90.f);

            Spell.TimingMode=TEXT("cast"); Spell.bCancelOnMovement=false; Spell.Shape=TEXT("melee"); Spell.Range=600; Install(); Reset();
            Runtime->UpdateMovementIntent(true); TestTrue(TEXT("Melee can start with movement held"),Runtime->TryActivate(Spell.Id,Target,Error));
            for (int I=0;I<25;++I) { Pawn->AddMovementInput(FVector(0,1,0),1); Advance(1.f/120); }
            TestTrue(TEXT("Melee animation permits real capsule movement"),Pawn->GetActorLocation().Y>10);
            TestTrue(TEXT("Melee survives movement"),Runtime->IsBusy());
            Target->SetActorLocation(FVector(2500,0,99)); Advance(.3f); TestEqual(TEXT("Melee checks range at contact"),Health(),2000.f);
            Target->SetActorLocation(FVector(400,0,99));

            Spell.Shape=TEXT("projectile"); Spell.Range=3000; Install(); Reset(); Runtime->TryActivate(Spell.Id,Target,Error);
            TestFalse(TEXT("Cannot buffer too early"),Runtime->QueueAbility(Followup.Id,Target,TEXT("fluid-test"),FVector::ZeroVector));
            Advance(.85f); Runtime->QueueAbility(Followup.Id,nullptr,TEXT("fluid-test"),FVector::ZeroVector); TestTrue(TEXT("Latest buffered target replaces the previous request within 200ms"),Runtime->QueueAbility(Followup.Id,Target,TEXT("fluid-test"),FVector::ZeroVector));
            Advance(.2f); TestEqual(TEXT("Buffered ability starts before old animation ends"),Runtime->GetCastingAbility(),Followup.Id);
            Reset(); Runtime->TryActivate(Spell.Id,Target,Error); Advance(.85f);
            Runtime->QueueAbility(Followup.Id,Target,TEXT("fluid-test"),FVector::ZeroVector); Runtime->UpdateMovementIntent(true); Advance(.3f);
            TestTrue(TEXT("Movement clears buffered input"),Runtime->GetCastingAbility().IsNone());

            auto* Other=Spawn(TEXT("/Game/MigrationProof/Visual_mire_warbrute_m"),FVector(0,200,99));
            if (Other)
            {
                Reset(); Target->SetActorLocation(FVector(200,0,99)); Runtime->TryActivate(Spell.Id,Target,Error); Advance(.85f);
                const float OtherHealth=Other->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth();
                Pawn->RequestTargetStrike(Target); Pawn->RequestTargetStrike(Other); Advance(2);
                TestEqual(TEXT("Rapid basic-attack replacement leaves the first target with only its spell hit"),Health(),1990.f);
                TestTrue(TEXT("Latest basic-attack press wins even within the request throttle"),Other->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth()<OtherHealth);
            }
            Pawn->MulticastPlayAbilityMotion(TEXT("attack_melee"),2,false); Pawn->SetAbilityPlaybackRate(2,false,.1f); Pawn->HoldAbilityPresentation(.2f,3,.5f);
            Pawn->HandleDeath();
            TestEqual(TEXT("Death does not inherit cast playback speed"),Pawn->GetReplicatedMotion().PlayRate,1.f);
            TestEqual(TEXT("Death does not inherit channel hold"),Pawn->GetReplicatedMotion().HoldDuration,0.f);
            TestEqual(TEXT("Death does not inherit instant release offset"),Pawn->GetReplicatedMotion().StartOffset,0.f);
        }
    }
    World->EndPlay(EEndPlayReason::Quit); Instance->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); Instance->RemoveFromRoot();
    return !HasAnyErrors();
}
#endif
