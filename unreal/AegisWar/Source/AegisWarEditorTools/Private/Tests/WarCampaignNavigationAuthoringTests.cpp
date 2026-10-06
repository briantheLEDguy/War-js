#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeAuthoringLibrary.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "NavMesh/RecastNavMesh.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCampaignNavigationAuthoringTest,"AegisWar.Foundation.CampaignNavigationOwnership",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCampaignNavigationAuthoringTest::RunTest(const FString& Parameters)
{
    const auto Pair=&UWarSiegeAuthoringLibrary::IsPrivateCampaignNavigationPair;
    const FString Root=TEXT("/Game/WorldRebuild/AegisCitadel_4069b99e5f8d/");
    TestTrue(TEXT("Exact private pair is admitted"),Pair(Root+TEXT("CampaignCandidate"),Root+TEXT("CampaignSiegeOverlay")));
    TestFalse(TEXT("Canonical map cannot transfer navigation"),Pair(TEXT("/Game/Capitals/AegisCapital"),Root+TEXT("CampaignSiegeOverlay")));
    TestFalse(TEXT("Scenario remains independent"),Pair(Root+TEXT("SiegeCandidate"),Root+TEXT("CampaignSiegeOverlay")));
    TestFalse(TEXT("Another revision cannot provide data"),Pair(Root+TEXT("CampaignCandidate"),TEXT("/Game/WorldRebuild/AegisCitadel_000000000000/CampaignSiegeOverlay")));
    TestFalse(TEXT("Revision length is exact"),Pair(TEXT("/Game/WorldRebuild/AegisCitadel_4069/CampaignCandidate"),Root+TEXT("CampaignSiegeOverlay")));
    TestFalse(TEXT("Null world does not mutate"),UWarSiegeAuthoringLibrary::OwnCampaignNavigation(nullptr,Root+TEXT("CampaignSiegeOverlay")).StartsWith(TEXT("{")));
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Editor,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Init);
    if (!TestNotNull(TEXT("Ownership guard fixture"),World)) return false;
    auto* Existing=World->SpawnActor<ARecastNavMesh>();const int32 Count=World->PersistentLevel->Actors.Num();
    TestFalse(TEXT("Unowned world cannot move an existing actor"),UWarSiegeAuthoringLibrary::OwnCampaignNavigation(World,Root+TEXT("CampaignSiegeOverlay")).StartsWith(TEXT("{")));
    TestTrue(TEXT("Rejected operation retains the actor"),Existing->GetLevel()==World->PersistentLevel);
    TestEqual(TEXT("Rejected operation preserves actor list"),World->PersistentLevel->Actors.Num(),Count);
    World->DestroyWorld(false);return true;
}
#endif
