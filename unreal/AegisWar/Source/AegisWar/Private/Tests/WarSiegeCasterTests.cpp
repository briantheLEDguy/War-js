#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityRuntime.h"
#include "WarAttributeSet.h"
#include "WarCombatStatus.h"
#include "WarWarpIdol.h"
#include "WarAnimationInstance.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeCasterTest,"AegisWar.Foundation.SiegeCasterGameplay",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarSiegeCasterTest::RunTest(const FString& Parameters)
{
    auto* Instance=NewObject<UGameInstance>(GEngine); Instance->AddToRoot(); Instance->InitializeStandalone();
    auto* World=Instance->GetWorld(); World->InitializeActorsForPlay(FURL()); World->BeginPlay(); World->GetWorldSettings()->NotifyBeginPlay();
    auto* Floor=World->SpawnActor<AActor>(); auto* Shape=NewObject<UBoxComponent>(Floor);
    Floor->SetRootComponent(Shape); Shape->SetBoxExtent(FVector(5000,5000,20)); Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Shape->SetCollisionObjectType(ECC_WorldStatic); Shape->SetCollisionResponseToAllChannels(ECR_Block);
    Shape->RegisterComponent(); Floor->SetActorLocation(FVector(0,0,-20));
    const auto Advance=[&](float Seconds) { for (int32 I=0;I<FMath::CeilToInt(Seconds*60);++I) { ++GFrameCounter; World->Tick(LEVELTICK_All,1.f/60); } };
    const auto Spawn=[&](const TCHAR* Path,FVector Position,bool Bot)
    {
        auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,Path);
        if (!TestNotNull(TEXT("Required authored native caster fixture"),Visual)) return static_cast<AWarCharacter*>(nullptr);
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=World->SpawnActor<AWarCharacter>(Position,FRotator::ZeroRotator,Params);
        AController* Controller=Bot ? static_cast<AController*>(World->SpawnActor<AAIController>()) : World->SpawnActor<APlayerController>();
        if (!Bot) CastChecked<APlayerController>(Controller)->SetPlayer(NewObject<ULocalPlayer>(GEngine));
        Controller->Possess(Pawn); auto* State=World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        FString Error; TestTrue(TEXT("Caster visual passes native validation"),Pawn->SetVisualDefinition(Visual,Error));
        State->InitializeForPawn(Pawn); State->SetSiegeNormalized(true); State->GetClassAbilities()->InitializeCharacter(Pawn);
        Pawn->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones; return Pawn;
    };
    int32 Executed=0;
    for (const TCHAR* Profile:{TEXT("riven_ruin_oracle_m"),TEXT("riven_void_magister_m")}) for (bool Bot:{false,true})
    {
        auto* Pawn=Spawn(*(FString(TEXT("/Game/Characters/SiegeStaging/Visual_"))+Profile),FVector(0,0,99),Bot);
        auto* Target=Spawn(TEXT("/Game/MigrationProof/Visual_civic_battle_prelate_m"),FVector(500,0,99),true);
        if (!Pawn || !Target) continue;
        auto* State=Pawn->GetPlayerState<AWarPlayerState>(); auto* Runtime=State->GetClassAbilities();
        const auto Kit=Instance->GetSubsystem<UWarAbilityCatalog>()->Kit(Pawn->GetCareerId());
        TestEqual(TEXT("Complete caster kit"),Kit.Num(),10);
        for (const auto* Ability:Kit)
        {
            Runtime->Interrupt(); Runtime->ResetCooldowns(); Runtime->RestoreResource(); AWarWarpIdol::RemoveFor(Pawn);
            UWarCombatStatus::On(Pawn)->Clear(); UWarCombatStatus::On(Target)->Clear();
            Pawn->SetActorLocation(FVector(0,0,99)); Pawn->SetActorRotation(FRotator::ZeroRotator);
            Pawn->GetCharacterMovement()->StopMovementImmediately(); Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            Target->SetActorLocation(FVector(Ability->Id==TEXT("void_magister.summon_idol") ? 500 : 200,0,99));
            if (Ability->Id==TEXT("void_magister.hover_disc")) Target->SetActorLocation(FVector(0,400,99));
            State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),1000);
            State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),1000);
            Target->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),2000); Advance(.2f);
            const auto* Recipe=Pawn->GetAbilityPresentation(Ability->Id);
            if (!TestNotNull(*Ability->Id.ToString(),Recipe)) continue;
            TestEqual(TEXT("Exact caster profile uses its own authored recipe"),WarAbilities::Motion(*Ability,FName(Profile)),Ability->Id);
            FString Error;
            if (Ability->Id==TEXT("void_magister.summon_idol"))
            {
                // Exercise advisory client availability without granting actor-spawn authority.
                Pawn->SwapRoles();
                TestFalse(TEXT("Preflight fixture has no pawn authority"),Pawn->HasAuthority());
                TestTrue(TEXT("Clients may request a deployable"),Runtime->CanActivate(*Ability,Pawn,Error,false));
                FVector Position;
                TestFalse(TEXT("Clients still cannot authorize placement"),AWarWarpIdol::Placement(Pawn,Position,Error));
                Pawn->SwapRoles();
            }
            if (!Runtime->TryActivate(Ability->Id,Ability->bEnemyTarget ? Target : Pawn,Error)) { AddError(Ability->Id.ToString()+TEXT(": ")+Error); continue; }
            // Stationary cast recipes follow validated travel; they do not replace its locomotion.
            if (Ability->Id==TEXT("void_magister.hover_disc"))
            {
                TestEqual(TEXT("Hover Disc begins grounded travel"),Pawn->GetReplicatedMotion().Role,FName(TEXT("run")));
                for (int32 Frame=0;Frame<180 && Pawn->GetReplicatedMotion().Role==TEXT("run");++Frame) Advance(1.f/60);
                TestTrue(TEXT("Hover Disc actually traverses the clear floor"),Pawn->GetActorLocation().X>300);
            }
            TestTrue(*(Ability->Id.ToString()+TEXT(" selects its recipe")),Recipe->VariantRoles.Contains(Pawn->GetReplicatedMotion().Role));
            Advance(Recipe->Duration+.5f); TestFalse(*(Ability->Id.ToString()+TEXT(" completes recovery")),Runtime->IsBusy());
            if (Ability->Effects.ContainsByPredicate([](const auto& E){return E.Kind==TEXT("damage");}))
                TestTrue(*Ability->Id.ToString(),Target->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth()<2000);
            if (Ability->Id==TEXT("void_magister.summon_idol"))
            {
                TestTrue(TEXT("Ability contact creates its actual native idol"),AWarWarpIdol::HasFor(Pawn));
                Advance(2.2f); TestTrue(TEXT("Summoned actor attacks after release"),Target->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth()<2000);
            }
            ++Executed;
        }
        AWarWarpIdol::RemoveFor(Pawn);
        Pawn->GetController()->Destroy(); Target->GetController()->Destroy(); Pawn->Destroy(); Target->Destroy(); Advance(.1f);
    }
    TestEqual(TEXT("Both complete caster kits execute for player and bot"),Executed,40);
    World->EndPlay(EEndPlayReason::Quit); Instance->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); Instance->RemoveFromRoot();
    return !HasAnyErrors();
}
#endif
