#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarAbilityRuntime.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarScenarioStateTest,"AegisWar.Foundation.ScenarioCharacterRecovery",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarScenarioStateTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());
    auto* State=World->SpawnActor<AWarPlayerState>();auto* Asc=State->GetAbilitySystemComponent();
    Asc->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),500);
    Asc->SetNumericAttributeBase(UWarAttributeSet::GetMaxManaAttribute(),200);
    Asc->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),123);
    Asc->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),47);
    auto Snapshot=State->CaptureScenarioState();
    auto Abilities=Snapshot->GetObjectField(TEXT("abilities"));
    auto Cooldown=MakeShared<FJsonObject>();Cooldown->SetStringField(TEXT("id"),TEXT("recovery.test"));Cooldown->SetNumberField(TEXT("remaining"),19);
    Abilities->SetArrayField(TEXT("cooldowns"),{MakeShared<FJsonValueObject>(Cooldown)});
    Asc->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),500);
    Asc->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),200);
    State->RestoreScenarioState(Snapshot);
    TestEqual(TEXT("Returning preserves campaign health"),State->GetAttributes()->GetHealth(),123.f);
    TestEqual(TEXT("Returning preserves campaign mana"),State->GetAttributes()->GetMana(),47.f);
    TestEqual(TEXT("Returning preserves remaining cooldown"),State->GetClassAbilities()->Cooldown(TEXT("recovery.test")),19.f);
    FString Error;const FGuid Receipt=FGuid::NewGuid();
    State->SetScenarioTransferPending(true);
    TestFalse(TEXT("Departure lock rejects campaign reward mutations"),State->GrantCharacterRewards(Receipt,1,1,{},Error));
    TestFalse(TEXT("Departure lock rejects level mutations"),State->SetGmLevelTrusted(20,Error));
    State->SetScenarioTransferPending(false);
    TestTrue(TEXT("Failed departure can restore ordinary campaign transactions"),State->GrantCharacterRewards(Receipt,1,1,{},Error));
    GEngine->DestroyWorldContext(World);World->DestroyWorld(false);return !HasAnyErrors();
}
#endif
