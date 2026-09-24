#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeRules.h"
#include "WarSiegeGameMode.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeRulesTest, "AegisWar.Foundation.SiegeRules",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarSiegeRulesTest::RunTest(const FString& Parameters)
{
    FWarSiegeState S; FWarSiegePresence P;
    TestFalse(TEXT("Unsupported capacity refused"), WarSiege::Start(S, 7));
    for (int32 N : {6, 12, 18})
    {
        S = {}; TestTrue(TEXT("Supported capacity"), WarSiege::Start(S, N));
        TestEqual(TEXT("Major NPC health scales"), WarSiege::HealthScale(N), N / 6.f);
        TestEqual(TEXT("Wave size scales"), WarSiege::Reinforcements(N, false), N / 3);
        TestEqual(TEXT("Sabotage halves waves"), WarSiege::Reinforcements(N, true), N / 6);
        TestFalse(TEXT("Active launch cannot reset progress"), WarSiege::Start(S, 6));
    }
    TestEqual(TEXT("Empty objective has no speed"), WarSiege::ParticipationRate(0), 0.f);
    TestEqual(TEXT("Capture participation capped"), WarSiege::ParticipationRate(18), 2.5f);
    TestEqual(TEXT("Escort participation capped"), WarSiege::ParticipationRate(18, true), 1.5f);
    S = {}; WarSiege::Start(S, 6); P.Attackers = 6; P.Defenders = 1;
    WarSiege::Tick(S, P, 30); TestEqual(TEXT("One defender contests six attackers"), S.Progress, 0.f);
    P.Defenders = 0; WarSiege::Tick(S, P, 10);
    TestTrue(TEXT("Presence accelerates capture"), FMath::IsNearlyEqual(S.Progress, .25f, .001f));
    P.Attackers = 0; WarSiege::Tick(S, P, 10);
    TestTrue(TEXT("Ten second grace preserves progress"), FMath::IsNearlyEqual(S.Progress, .25f, .001f));
    WarSiege::Tick(S, P, 2); TestTrue(TEXT("Then decay at five percent per second"), FMath::IsNearlyEqual(S.Progress, .15f, .001f));
    S = {}; WarSiege::Start(S, 6); P = {}; P.Attackers = 6;
    WarSiege::Tick(S, P, 41); TestEqual(TEXT("Supply advances to first checkpoint"), S.Objective, 1);
    P.bCrewAlive = false; WarSiege::Tick(S, P, 20); TestEqual(TEXT("Dead crew cannot advance"), S.Progress, 0.f);
    P.bCrewAlive = true;
    P.bEscortAtCheckpoint = false;
    WarSiege::Tick(S, P, 100);
    TestEqual(TEXT("Escort must physically reach its checkpoint"), S.Objective, 1);
    TestTrue(TEXT("Escort timer alone cannot complete the checkpoint"), S.Progress < 1.f);
    P.bEscortAtCheckpoint = true;
    for (int32 I = 0; I < 3; ++I) WarSiege::Tick(S, P, 100);
    TestEqual(TEXT("Breach completes lower city"), S.Phase, EWarSiegePhase::Transition);
    WarSiege::Tick(S, {}, 60); TestEqual(TEXT("Courtyard starts"), S.Stage, 1);
    TestEqual(TEXT("Stage timer resets"), S.Remaining, WarSiege::StageSeconds);
    TestEqual(TEXT("Capture state resets"), S.Progress, 0.f);
    for (int32 I = 0; I < 3; ++I) WarSiege::Tick(S, P, 100);
    WarSiege::Tick(S, {}, 60); TestEqual(TEXT("Commander stage starts"), S.Stage, 2);
    P.bCommanderDead = true; WarSiege::Tick(S, P, 1);
    TestTrue(TEXT("Commander death wins"), S.bAttackersWon);
    WarSiege::Tick(S, P, 100); TestEqual(TEXT("Result emitted exactly once"), S.ResultCount, 1);
    for (int32 Stage = 0; Stage < 3; ++Stage)
    {
        S = {}; WarSiege::Start(S, 6); S.Stage = Stage; S.Remaining = .5; P = {};
        WarSiege::Tick(S, P, 1); TestEqual(TEXT("Defenders can win each stage"), S.Phase, EWarSiegePhase::Finished);
        TestFalse(TEXT("Timeout is defender victory"), S.bAttackersWon);
        S = {}; WarSiege::Start(S, 6); S.Stage = Stage; S.Objective = WarSiege::FinalObjective(Stage); S.Remaining = .5;
        P.Attackers = 1; P.Defenders = 1; P.bRecentCommanderDamage = true;
        WarSiege::Tick(S, P, 1); TestTrue(TEXT("Final objective activity grants overtime"), S.bOvertime);
        P.Attackers = 0; P.bRecentCommanderDamage = false;
        WarSiege::Tick(S, P, 10.1); TestEqual(TEXT("Overtime ends on absence"), S.Phase, EWarSiegePhase::Finished);
        S = {}; WarSiege::Start(S, 6); S.Stage = Stage; S.Objective = WarSiege::FinalObjective(Stage); S.Remaining = .5;
        P.Attackers = 1; P.Defenders = 1; P.bRecentCommanderDamage = true;
        WarSiege::Tick(S, P, 121); TestEqual(TEXT("Active overtime still bounded"), S.Phase, EWarSiegePhase::Finished);
    }
    S = {}; WarSiege::Start(S, 6); P = {}; P.OptionalAttackers = 6;
    WarSiege::Tick(S, P, 41); TestTrue(TEXT("Optional objective completes independently"), S.bOptionalComplete);
    WarSiege::Tick(S, {}, 60); TestTrue(TEXT("Completed optional task persists"), S.bOptionalComplete);
    TestEqual(TEXT("Optional task never advances required chain"), S.Objective, 0);
    FWarSiegeState Small, Large; WarSiege::Start(Small,6); WarSiege::Start(Large,6); P = {}; P.Attackers = 1;
    WarSiege::Tick(Large,P,10); for (int32 I=0; I<100; ++I) WarSiege::Tick(Small,P,.1);
    TestTrue(TEXT("Frame-rate independent capture"), FMath::IsNearlyEqual(Small.Progress,Large.Progress,.0001f));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeBotRulesTest, "AegisWar.Foundation.SiegeBotRules",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarSiegeBotRulesTest::RunTest(const FString& Parameters)
{
    TestEqual(TEXT("Fill tank deficit"), WarSiege::MissingRole(18,2,0), EWarSiegeRole::Tank);
    TestEqual(TEXT("Then healer deficit"), WarSiege::MissingRole(18,3,2), EWarSiegeRole::Healer);
    TestEqual(TEXT("Then damage"), WarSiege::MissingRole(18,3,3), EWarSiegeRole::Damage);
    TestEqual(TEXT("Hazards before combat"), WarSiege::Decide(true,false,1,true,true,true), EWarSiegeDecision::Evade);
    TestEqual(TEXT("Critical health before combat"), WarSiege::Decide(false,false,.2,true,true,true), EWarSiegeDecision::Recover);
    TestEqual(TEXT("Recovery hysteresis"), WarSiege::Decide(false,true,.5,true,true,true), EWarSiegeDecision::Recover);
    TestEqual(TEXT("Healthy combat before objective"), WarSiege::Decide(false,true,.65,true,true,true), EWarSiegeDecision::Combat);
    TestEqual(TEXT("Nearby objective before following"), WarSiege::Decide(false,false,1,false,true,true), EWarSiegeDecision::Objective);
    TestEqual(TEXT("No human still advances"), WarSiege::Decide(false,false,1,false,false,false), EWarSiegeDecision::Objective);
    TestEqual(TEXT("Otherwise follow"), WarSiege::Decide(false,false,1,false,false,true), EWarSiegeDecision::Follow);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeAuthorityTest, "AegisWar.Foundation.SiegeAuthorityAndNormalization",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarSiegeAuthorityTest::RunTest(const FString& Parameters)
{
    auto* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Test world"), World)) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Mode = World->SpawnActor<AWarSiegeGameMode>(); FString Error;
    TestFalse(TEXT("Unauthenticated launch rejected"), Mode->Launch(nullptr,6,1,Error));
    TestFalse(TEXT("Unauthenticated reset rejected"), Mode->ResetSiege(nullptr,Error));
    auto* Battlefield = World->SpawnActor<AWarSiegeBattlefield>();
    auto* Outer = World->SpawnActor<AActor>();
    auto* Inner = World->SpawnActor<AActor>();
    Battlefield->StageGates = {Outer, Inner};
    FWarSiegeState Siege;
    Battlefield->ApplyMilestones(Siege);
    TestTrue(TEXT("Outer blockade starts closed"), Outer->GetActorEnableCollision());
    TestTrue(TEXT("Inner blockade starts closed"), Inner->GetActorEnableCollision());
    Siege.Phase = EWarSiegePhase::Transition;
    Battlefield->ApplyMilestones(Siege);
    TestFalse(TEXT("Lower city victory opens outer blockade"), Outer->GetActorEnableCollision());
    TestTrue(TEXT("Inner blockade stays closed"), Inner->GetActorEnableCollision());
    Siege.Stage = 1;
    Battlefield->ApplyMilestones(Siege);
    TestFalse(TEXT("Courtyard victory opens inner blockade"), Inner->GetActorEnableCollision());
    Siege = {};
    Battlefield->ApplyMilestones(Siege);
    TestTrue(TEXT("Reset restores outer blockade"), Outer->GetActorEnableCollision());
    TestTrue(TEXT("Reset restores inner blockade"), Inner->GetActorEnableCollision());
    auto* State = World->SpawnActor<AWarPlayerState>();
    const auto Before = State->GetInventory();
    State->SetSiegeNormalized(true);
    TestEqual(TEXT("Normalized combat level"), State->GetCombatLevel(),40);
    TestEqual(TEXT("Normalized strength"), State->GetEffectiveStrength(),int64(100));
    TestEqual(TEXT("Saved level unchanged"), State->GetInventory().CharacterProgression.Level,Before.CharacterProgression.Level);
    TestEqual(TEXT("Saved inventory revision unchanged"), State->GetInventory().Revision,Before.Revision);
    TestFalse(TEXT("Siege cannot grant persistent rewards"), State->GrantCharacterRewards(FGuid::NewGuid(),100,100,{},Error));
    State->SetSiegeNormalized(false);
    TestEqual(TEXT("Combat level restored"), State->GetCombatLevel(),Before.CharacterProgression.Level);
    return true;
}
#endif
