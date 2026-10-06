#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCampaignRecoverySpawnTest,"AegisWar.Foundation.CampaignRecoverySpawn",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCampaignRecoverySpawnTest::RunTest(const FString& Parameters)
{
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Editor,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Init);
    if (!TestNotNull(TEXT("Recovery admission fixture"),World)) return false;
    auto* Bridge=NewObject<UWarCampaignSiegeSubsystem>(World);
    auto* Recovering=World->SpawnActor<AWarPlayerController>();auto* Other=World->SpawnActor<AWarPlayerController>();
    auto* State=World->SpawnActor<AWarPlayerState>();Recovering->PlayerState=State;State->SetOwner(Recovering);
    Recovering->ScenarioCharacterId=TEXT("recorded-participant");Other->ScenarioCharacterId=TEXT("other-zone-player");
    State->SetScenarioTransferPending(true);
    UWarCampaignSiegeSubsystem::FRecovery Record;Record.Player=Recovering;Record.Character=MakeShared<FJsonObject>();
    Bridge->Recoveries.Add(Recovering->ScenarioCharacterId,Record);
    FTransform Arrival(FRotator(0,45,0),FVector(10,20,30));const FTransform Original=Arrival;
    bool IsRecovery=true;FString Error;
    TestTrue(TEXT("Unrelated player retains ordinary entry"),Bridge->ResolveRecoverySpawn(Other,Arrival,IsRecovery,Error));
    TestFalse(TEXT("Unrelated identity is outside the recovery override"),IsRecovery);
    TestTrue(TEXT("Unrelated arrival transform is unchanged"),Arrival.Equals(Original));
    TestFalse(TEXT("Recovering participant cannot fall through to a crowded login start without ownership"),
        Bridge->ResolveRecoverySpawn(Recovering,Arrival,IsRecovery,Error));
    TestTrue(TEXT("The waiting identity stays marked as recovering"),IsRecovery);
    TestTrue(TEXT("Unready ownership retains the arrival transform"),Arrival.Equals(Original));
    TestTrue(TEXT("Recovery custody stays protected"),State->IsScenarioTransferPending());
    Bridge->bOwnerLeaseReady=true;
    TestFalse(TEXT("A lease alone does not bypass scene and navigation readiness"),
        Bridge->ResolveRecoverySpawn(Recovering,Arrival,IsRecovery,Error));
    TestTrue(TEXT("Scene failure preserves the held document"),Bridge->Recoveries.Contains(Recovering->ScenarioCharacterId));
    TestTrue(TEXT("Scene failure preserves character custody"),State->IsScenarioTransferPending());
    TestFalse(TEXT("Spawn selection never normalizes campaign characters"),State->IsSiegeNormalized());
    World->DestroyWorld(false);return true;
}
#endif
