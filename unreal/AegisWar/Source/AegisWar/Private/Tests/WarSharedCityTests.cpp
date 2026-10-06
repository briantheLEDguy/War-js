#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCityDefinition.h"
#include "WarZoneLightingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarQuestNpc.h"
#include "WarSiegeBattlefield.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/StaticMeshActor.h"
#include "Components/VolumetricCloudComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSharedCityTest, "AegisWar.Foundation.SharedCity",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)
bool FWarSharedCityTest::RunTest(const FString& Parameters)
{
    auto* City = NewObject<UWarCityDefinition>();
    FString Error;
    TestFalse(TEXT("No empty city fallback"), City->Validate(Error));
    City->ZoneId = TEXT("aegis_capital"); City->Revision = TEXT("current");
    City->SceneryLevels.Add(TSoftObjectPtr<UWorld>(FSoftObjectPath(TEXT("/Game/Test/Scenery.Scenery"))));
    TestTrue(TEXT("One canonical scenery reference"), City->Validate(Error));
    const auto DuplicateLevel = City->SceneryLevels[0];
    City->SceneryLevels.Add(DuplicateLevel);
    TestFalse(TEXT("Repeated level is rejected"), City->Validate(Error));
    City->SceneryLevels.Pop();
    TestFalse(TEXT("Quest actors never enter city presentation"), UWarCityDefinition::IsSceneryActor(GetDefault<AWarQuestNpc>()));
    TestFalse(TEXT("Siege objectives never enter shared scenery"), UWarCityDefinition::IsSceneryActor(GetDefault<AWarSiegeBattlefield>()));
    TestTrue(TEXT("Native scenery is allowed"), UWarCityDefinition::IsSceneryActor(GetDefault<AStaticMeshActor>()));
    TestTrue(TEXT("Exact native volumetric cloud is shared scenery"),
        UWarCityDefinition::IsSceneryActor(GetDefault<AVolumetricCloud>()));
    TestFalse(TEXT("Cloud allowance does not admit generic actors"),
        UWarCityDefinition::IsSceneryActor(GetDefault<AActor>()));
    auto* CloudLevel = NewObject<ULevel>();
    CloudLevel->Actors.Add(GetMutableDefault<AVolumetricCloud>());
    TestTrue(TEXT("Cloud-only shared scenery validates without a substitute mesh"),
        UWarCityDefinition::ValidateLevel(CloudLevel, Error));
    CloudLevel->Actors.Add(GetMutableDefault<AWarSiegeBattlefield>());
    TestFalse(TEXT("Cloud scenery still rejects gameplay in the same level"),
        UWarCityDefinition::ValidateLevel(CloudLevel, Error));
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World = UWorld::CreateWorld(EWorldType::Editor, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("City routing fixture"), World)) return false;
    auto* Anchor = World->SpawnActor<AWarZoneAnchor>();
    Anchor->ZoneId = City->ZoneId;
    Anchor->CityDefinition = City;
    Anchor->ContentLevels.Add(TEXT("/Game/Test/Services"));
    TestEqual(TEXT("Campaign resolves services plus canonical scenery"), Anchor->GetContentLevels().Num(), 2);
    City->SceneryLevels[0] = TSoftObjectPtr<UWorld>(FSoftObjectPath(TEXT("/Game/Test/Updated.Updated")));
    TestEqual(TEXT("Campaign immediately resolves updated city reference"), Anchor->GetContentLevels()[1], FName(TEXT("/Game/Test/Updated")));
    TestTrue(TEXT("Canonical campaign binding is valid"), Anchor->ValidateCity(Error));
    Anchor->ContentLevels.Add(TEXT("/Game/Test/Updated"));
    TestFalse(TEXT("Scenery duplicated in campaign overlay is rejected"), Anchor->ValidateCity(Error));
    Anchor->ContentLevels.Pop();
    Anchor->CityDefinition = nullptr;
    TestFalse(TEXT("Capital without a shared definition is recoverable"), Anchor->ValidateCity(Error));
    World->DestroyWorld(false);
    auto* Preview = UWorld::CreateWorld(EWorldType::GamePreview, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (TestNotNull(TEXT("Isolated presentation world"), Preview))
    {
        TestTrue(TEXT("Presentation uses campaign Riftspire lighting profile"),
            UWarZoneLightingSubsystem::PreviewWorld(Preview, TEXT("riftspire_capital"), FVector(1600000,600000,0)));
        TestEqual(TEXT("Exact profile selected"), Preview->GetSubsystem<UWarZoneLightingSubsystem>()->GetActiveZone(), FName(TEXT("riftspire_capital")));
        Preview->DestroyWorld(false);
    }
    return true;
}
#endif
