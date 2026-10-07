#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeAuthoringLibrary.h"
#include "WarImportLibrary.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/LevelStreamingDynamic.h"
#include "NavMesh/RecastNavMesh.h"
#include "UObject/Package.h"

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

    TestTrue(TEXT("A valid world with no declarations returns an empty inventory"),UWarImportLibrary::GetStreamingLevelPackageNames(World).IsEmpty());
    const auto Declare=[World](const TCHAR* Package,bool bLoad,bool bVisible)
    {
        auto* Level=NewObject<ULevelStreamingDynamic>(World);
        Level->SetWorldAssetByPackageName(FName(Package));World->AddStreamingLevel(Level);
        Level->SetShouldBeLoaded(bLoad);Level->SetShouldBeVisible(bVisible);
        return Level;
    };
    Declare(TEXT("/Game/Tests/Streaming/Zulu"),true,false);
    Declare(TEXT("/Game/Tests/Streaming/Alpha"),false,true);
    Declare(TEXT("/Game/Tests/Streaming/Alpha"),false,false);
    const auto DeclarationsBefore=World->GetStreamingLevels();
    const bool bDirtyBefore=World->GetOutermost()->IsDirty();
    struct FDeclarationState { bool bLoaded,bVisible,bWantLoaded,bWantVisible; };
    TArray<FDeclarationState> StatesBefore;
    for (const ULevelStreaming* Level:DeclarationsBefore)
    {
        TestFalse(TEXT("Inventory fixture declaration is actually unloaded"),Level->IsLevelLoaded());
        StatesBefore.Add({Level->IsLevelLoaded(),Level->IsLevelVisible(),Level->ShouldBeLoaded(),Level->GetShouldBeVisibleFlag()});
    }
    const TArray<FString> Expected={TEXT("/Game/Tests/Streaming/Alpha"),TEXT("/Game/Tests/Streaming/Alpha"),TEXT("/Game/Tests/Streaming/Zulu")};
    TestTrue(TEXT("Inventory includes every unloaded declaration, sorts names and retains duplicates"),UWarImportLibrary::GetStreamingLevelPackageNames(World)==Expected);
    TestTrue(TEXT("Inventory preserves the streaming declaration array and order"),World->GetStreamingLevels()==DeclarationsBefore);
    TestEqual(TEXT("Inventory preserves world package dirtiness"),World->GetOutermost()->IsDirty(),bDirtyBefore);
    for (int32 Index=0;Index<DeclarationsBefore.Num();++Index)
    {
        const ULevelStreaming* Level=DeclarationsBefore[Index];const auto& State=StatesBefore[Index];
        TestEqual(TEXT("Inventory preserves actual loaded state"),Level->IsLevelLoaded(),State.bLoaded);
        TestEqual(TEXT("Inventory preserves actual visible state"),Level->IsLevelVisible(),State.bVisible);
        TestEqual(TEXT("Inventory preserves desired loading"),Level->ShouldBeLoaded(),State.bWantLoaded);
        TestEqual(TEXT("Inventory preserves desired visibility"),Level->GetShouldBeVisibleFlag(),State.bWantVisible);
        TestFalse(TEXT("Inventory never requests an asset load"),Level->HasLoadRequestPending());
    }
    AddExpectedError(TEXT("Streaming level package inspection requires a valid world."),EAutomationExpectedErrorFlags::Contains,1);
    TestTrue(TEXT("Invalid world fails with an explicit error and empty result"),UWarImportLibrary::GetStreamingLevelPackageNames(nullptr).IsEmpty());
    ULevelStreaming* InvalidDeclaration=DeclarationsBefore.Last();InvalidDeclaration->MarkAsGarbage();
    AddExpectedError(TEXT("Streaming level package inspection encountered an invalid declaration."),EAutomationExpectedErrorFlags::Contains,1);
    TestTrue(TEXT("Invalid declaration fails explicitly instead of returning an incomplete inventory"),UWarImportLibrary::GetStreamingLevelPackageNames(World).IsEmpty());
    TestTrue(TEXT("Rejected inventory preserves the declaration array"),World->GetStreamingLevels()==DeclarationsBefore);
    TestEqual(TEXT("Rejected inventory preserves package dirtiness"),World->GetOutermost()->IsDirty(),bDirtyBefore);
    TestFalse(TEXT("Inspection cannot revive an invalid declaration"),IsValid(InvalidDeclaration));
    InvalidDeclaration->ClearGarbage();
    World->DestroyWorld(false);return true;
}
#endif
