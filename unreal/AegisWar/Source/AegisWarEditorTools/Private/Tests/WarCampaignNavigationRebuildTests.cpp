#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeAuthoringLibrary.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "NavMesh/RecastNavMesh.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCampaignNavigationRebuildTest,"AegisWar.Foundation.CampaignNavigationRebuild",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCampaignNavigationRebuildTest::RunTest(const FString&)
{
    const FString Overlay=TEXT("/Game/WorldRebuild/AegisCitadel_62df5e965e66/CampaignSiegeOverlay");
    const FString Revision=TEXT("e798f5697d6f2e6d1a9ddf1a9d81920a067d0f3bbf9e9fc024bdef3b158988d6");
    TestFalse(TEXT("Null editor context cannot rebuild"),UWarSiegeAuthoringLibrary::RebuildCampaignNavigation(
        nullptr,Overlay,Revision,{},{}).StartsWith(TEXT("{")));
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Editor,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Init);
    if (!TestNotNull(TEXT("Unowned editor fixture"),World)) return false;
    auto* Existing=World->SpawnActor<ARecastNavMesh>();
    const auto Actors=World->PersistentLevel->Actors;const bool Dirty=World->GetOutermost()->IsDirty();
    TestFalse(TEXT("Unowned editor world cannot rebuild"),UWarSiegeAuthoringLibrary::RebuildCampaignNavigation(
        World,Overlay,Revision,{Overlay},{Overlay}).StartsWith(TEXT("{")));
    TestTrue(TEXT("Rejected rebuild retains every actor"),World->PersistentLevel->Actors==Actors);
    TestTrue(TEXT("Rejected rebuild retains navigation ownership"),Existing->GetLevel()==World->PersistentLevel);
    TestEqual(TEXT("Rejected rebuild retains package dirtiness"),World->GetOutermost()->IsDirty(),Dirty);
    World->DestroyWorld(false);
    return true;
}
#endif
