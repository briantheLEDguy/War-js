#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "WarGameplayEffects.h"
#include "WarAttributeSet.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarGameMode.h"
#include "WarStrikeAbility.h"
#include "WarTypes.h"
#include "AbilitySystemComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"

namespace
{
    FString ManifestFixture()
    {
        return TEXT("{\"schemaVersion\":1,\"source\":{\"sha256\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"},")
            TEXT("\"maps\":[{\"id\":\"aegis_capital\",\"sourcePath\":\"public/assets/maps/aegis_capital.json\",\"definition\":{\"id\":\"aegis_capital\"}}],")
            TEXT("\"developmentMaps\":[],\"careers\":{\"classes\":[{}]},\"abilities\":{\"definitions\":[{},{}]},")
            TEXT("\"items\":{\"definitions\":[{}]},\"quests\":[{}],\"crafting\":{\"recipes\":[{}]}}");
    }

    FString VisualImportFixture()
    {
        return TEXT("{\"schemaVersion\":1,\"entries\":[{\"profileKey\":\"civic_battle_prelate_m\",")
            TEXT("\"sourceModel\":\"public/assets/models/authored-prelate.glb\",")
            TEXT("\"sourceSha256\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",")
            TEXT("\"skeletalMeshPath\":\"/Game/Characters/Prelate.Prelate\",")
            TEXT("\"animationPaths\":[\"/Game/Characters/Prelate_Idle.Prelate_Idle\"]}]}");
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarVisualImportBindingTest, "AegisWar.Foundation.VerifiedVisualImportBindings",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarVisualImportBindingTest::RunTest(const FString& Parameters)
{
    TMap<FName, FWarVisualImportBinding> Bindings;
    FString Error;
    TestTrue(TEXT("An actual import receipt shape parses"), UWarContentSubsystem::ParseVisualImports(VisualImportFixture(), Bindings, Error));
    TestEqual(TEXT("One unique profile binding"), Bindings.Num(), 1);
    TestFalse(TEXT("Malformed hash is rejected"), UWarContentSubsystem::ParseVisualImports(
        VisualImportFixture().Replace(TEXT("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"), TEXT("not-a-hash")), Bindings, Error));
    TestEqual(TEXT("Rejected registry does not preserve earlier entries"), Bindings.Num(), 0);
    TestFalse(TEXT("Engine mesh is not an imported character"), UWarContentSubsystem::ParseVisualImports(
        VisualImportFixture().Replace(TEXT("/Game/Characters/Prelate.Prelate"), TEXT("/Engine/BasicShapes/Cube.Cube")), Bindings, Error));
    UWarCharacterVisualDefinition* Visual = NewObject<UWarCharacterVisualDefinition>();
    Visual->ProfileKey = TEXT("civic_battle_prelate_m");
    Visual->SourceModel = TEXT("public/assets/models/authored-prelate.glb");
    Visual->SourceSha256 = FString::ChrN(64, TEXT('a'));
    TestFalse(TEXT("Absent binding refuses entry"), UWarContentSubsystem::ValidateVisualImportBinding(Visual, Bindings, Error));
    TestTrue(TEXT("Absence explains the import requirement"), Error.Contains(TEXT("no verified import binding")));
    UWarContentSubsystem::ParseVisualImports(VisualImportFixture(), Bindings, Error);
    Visual->SourceSha256 = FString::ChrN(64, TEXT('b'));
    TestFalse(TEXT("Syntactically valid but wrong source hash refuses entry"), UWarContentSubsystem::ValidateVisualImportBinding(Visual, Bindings, Error));
    TestTrue(TEXT("Wrong hash identifies the mismatched proof"), Error.Contains(TEXT("source model/hash")));
    Visual->SourceSha256 = FString::ChrN(64, TEXT('a'));
    Visual->SkeletalMesh = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(TEXT("/Game/Characters/Unverified.Unverified")));
    TestFalse(TEXT("Matching source metadata cannot attest a different mesh"), UWarContentSubsystem::ValidateVisualImportBinding(Visual, Bindings, Error));
    TestTrue(TEXT("Wrong mesh identifies the mismatched binding"), Error.Contains(TEXT("skeletal mesh differs")));
    Visual->SkeletalMesh = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(TEXT("/Game/Characters/Prelate.Prelate")));
    Visual->IdleAnimation = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(TEXT("/Game/Characters/Unverified_Idle.Unverified_Idle")));
    TestFalse(TEXT("Unverified animation refuses entry before loading a mesh"), UWarContentSubsystem::ValidateVisualImportBinding(Visual, Bindings, Error));
    TestTrue(TEXT("Wrong animation identifies the mismatched binding"), Error.Contains(TEXT("animation differs")));
    Visual->IdleAnimation = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(TEXT("/Game/Characters/Prelate_Idle.Prelate_Idle")));
    Visual->ImportedAnimations.Add(TEXT("run"), TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(TEXT("/Game/Characters/Unverified_Run.Unverified_Run"))));
    TestFalse(TEXT("An unverified locomotion clip cannot bypass the idle binding"), UWarContentSubsystem::ValidateVisualImportBinding(Visual, Bindings, Error));
    TestTrue(TEXT("Wrong locomotion identifies the mismatched set"), Error.Contains(TEXT("animation set differs")));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarContentContractTest, "AegisWar.Foundation.ContentContract",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarContentContractTest::RunTest(const FString& Parameters)
{
    FWarContentSummary Summary;
    FString Error;
    TestTrue(TEXT("Portable schema loads"), UWarContentSubsystem::ParseManifest(ManifestFixture(), Summary, Error));
    TestEqual(TEXT("World count comes from the exported catalog"), Summary.MapCount, 1);
    TestEqual(TEXT("Definitions are counted without claiming they execute"), Summary.AbilityCount, 2);
    TestFalse(TEXT("Unknown schema fails closed"), UWarContentSubsystem::ParseManifest(ManifestFixture().Replace(TEXT("\"schemaVersion\":1"), TEXT("\"schemaVersion\":2")), Summary, Error));
    TestEqual(TEXT("Rejected parse clears earlier state"), Summary.MapCount, 0);
    TestFalse(TEXT("Malformed JSON does not crash"), UWarContentSubsystem::ParseManifest(TEXT("[]"), Summary, Error));
    TestFalse(TEXT("Missing provenance is rejected"), UWarContentSubsystem::ParseManifest(ManifestFixture().Replace(TEXT("sha256"), TEXT("missing")), Summary, Error));
    TestFalse(TEXT("Missing catalog is rejected"), UWarContentSubsystem::ParseManifest(ManifestFixture().Replace(TEXT("\"quests\""), TEXT("\"unknown\"")), Summary, Error));
    TestFalse(TEXT("Map definition cannot change identity"), UWarContentSubsystem::ParseManifest(ManifestFixture().Replace(TEXT("\"definition\":{\"id\":\"aegis_capital\"}"), TEXT("\"definition\":{\"id\":\"another_zone\"}")), Summary, Error));
    const FString Duplicate = ManifestFixture().Replace(TEXT("\"developmentMaps\":[]"),
        TEXT("\"developmentMaps\":[{\"id\":\"aegis_capital\",\"sourcePath\":\"duplicate.json\",\"definition\":{\"id\":\"aegis_capital\"}}]"));
    TestFalse(TEXT("IDs cannot collide between campaign and development maps"), UWarContentSubsystem::ParseManifest(Duplicate, Summary, Error));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatBoundaryTest, "AegisWar.Foundation.CombatBoundaries",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarCombatBoundaryTest::RunTest(const FString& Parameters)
{
    using namespace WarValidation;
    TestTrue(TEXT("Living enemy in range is eligible"), CanStrike(EWarRealm::Aegis, EWarRealm::Riftbound, 100.f, 100.f, 90000., true, false));
    TestFalse(TEXT("Range is server-owned"), CanStrike(EWarRealm::Aegis, EWarRealm::Riftbound, 100.f, 100.f, 90001., true, false));
    TestFalse(TEXT("Walls block damage"), CanStrike(EWarRealm::Aegis, EWarRealm::Riftbound, 100.f, 100.f, 1., false, false));
    TestFalse(TEXT("Friendly fire rejected"), CanStrike(EWarRealm::Aegis, EWarRealm::Aegis, 100.f, 100.f, 1., true, false));
    TestFalse(TEXT("Unassigned identity rejected"), CanStrike(EWarRealm::None, EWarRealm::Riftbound, 100.f, 100.f, 1., true, false));
    TestFalse(TEXT("Dead attacker rejected"), CanStrike(EWarRealm::Aegis, EWarRealm::Riftbound, 0.f, 100.f, 1., true, false));
    TestFalse(TEXT("Dead target rejected"), CanStrike(EWarRealm::Aegis, EWarRealm::Riftbound, 100.f, 0.f, 1., true, false));
    TestFalse(TEXT("Self target rejected"), CanStrike(EWarRealm::Aegis, EWarRealm::Riftbound, 100.f, 100.f, 1., true, true));
    TestFalse(TEXT("Negative squared distance rejected"), CanStrike(EWarRealm::Aegis, EWarRealm::Riftbound, 100.f, 100.f, -1., true, false));
    const UWarStrikeAbility* Strike = GetDefault<UWarStrikeAbility>();
    TestEqual(TEXT("Ability executes only on authority"), Strike->GetNetExecutionPolicy(), EGameplayAbilityNetExecutionPolicy::ServerOnly);
    TestEqual(TEXT("Clients cannot invoke GAS activation directly"), Strike->GetNetSecurityPolicy(), EGameplayAbilityNetSecurityPolicy::ServerOnly);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAdmissionTest, "AegisWar.Foundation.ClosedProductionAdmission",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarAdmissionTest::RunTest(const FString& Parameters)
{
    TestFalse(TEXT("No implicit development network"), WarValidation::AllowsDevelopmentNetwork(false, false));
    TestTrue(TEXT("Explicit non-shipping development network"), WarValidation::AllowsDevelopmentNetwork(false, true));
    TestFalse(TEXT("Shipping cannot activate development bypass"), WarValidation::AllowsDevelopmentNetwork(true, true));
    TestFalse(TEXT("Shipping stays closed without production authentication"), WarValidation::AllowsDevelopmentNetwork(true, false));
    TestTrue(TEXT("IPv4 loopback proof"), AWarGameMode::IsLoopbackProofAddress(TEXT("127.0.0.1")));
    TestTrue(TEXT("IPv6 loopback proof"), AWarGameMode::IsLoopbackProofAddress(TEXT("::1")));
    TestFalse(TEXT("VPN clients cannot use proof flags"), AWarGameMode::IsLoopbackProofAddress(TEXT("100.64.1.2")));
    TestFalse(TEXT("LAN clients cannot use proof flags"), AWarGameMode::IsLoopbackProofAddress(TEXT("192.168.1.10")));
    TestFalse(TEXT("Address prefix spoofing"), AWarGameMode::IsLoopbackProofAddress(TEXT("127.0.0.1.evil.example")));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarVisualGateTest, "AegisWar.Foundation.NoPrimitiveVisualFallback",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarVisualGateTest::RunTest(const FString& Parameters)
{
    UWarCharacterVisualDefinition* Visual = NewObject<UWarCharacterVisualDefinition>();
    FString Error;
    TestFalse(TEXT("Empty visual cannot spawn"), Visual->ValidateForSpawn(EWarRealm::Aegis, Error));
    Visual->ProfileKey = TEXT("test_prelate_m");
    Visual->RaceId = TEXT("empire");
    Visual->ClassId = TEXT("battle_prelate");
    Visual->BodyVariant = TEXT("m");
    Visual->Realm = EWarRealm::Aegis;
    Visual->SourceModel = TEXT("authored-prelate.glb");
    Visual->SourceSha256 = FString::ChrN(64, TEXT('a'));
    TestFalse(TEXT("Authorship is explicitly required"), Visual->ValidateForSpawn(EWarRealm::Aegis, Error));
    Visual->bComplexAuthoredModel = true;
    TestFalse(TEXT("A metadata-only entry cannot hide a missing mesh"), Visual->ValidateForSpawn(EWarRealm::Aegis, Error));
    Visual->SourceModel = TEXT("primitive-proxy.glb");
    TestFalse(TEXT("Proxy source cannot be promoted by setting a flag"), Visual->ValidateForSpawn(EWarRealm::Aegis, Error));
    TestFalse(TEXT("Opposing realm identity cannot be substituted"), Visual->ValidateForSpawn(EWarRealm::Riftbound, Error));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityOwnershipTest, "AegisWar.Foundation.PlayerStateAbilityOwnership",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarAbilityOwnershipTest::RunTest(const FString& Parameters)
{
    if (!TestNotNull(TEXT("Engine is available for GAS world test"), GEngine)) return false;
    const UWorld::InitializationValues Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Test world"), World)) return false;
    FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
    Context.SetCurrentWorld(World);
    // Match the engine's GAS fixtures: component initialization discovers default attribute-set subobjects.
    World->InitializeActorsForPlay(FURL());
    World->BeginPlay();
    AWarPlayerState* State = World->SpawnActor<AWarPlayerState>();
    AActor* FirstAvatar = World->SpawnActor<AActor>();
    AActor* SecondAvatar = World->SpawnActor<AActor>();
    UAbilitySystemComponent* ASC = State->GetAbilitySystemComponent();
    TestTrue(TEXT("ASC completed component initialization"), ASC->HasBeenInitialized());
    TestEqual(TEXT("The PlayerState attribute subobject is registered with GAS"), ASC->GetSet<UWarAttributeSet>(), State->GetAttributes());
    ASC->InitAbilityActorInfo(State, FirstAvatar);
    ASC->ApplyGameplayEffectToSelf(GetDefault<UWarInitialAttributesEffect>(), 1.f, ASC->MakeEffectContext());
    TestEqual(TEXT("Authority initializes health"), State->GetAttributes()->GetHealth(), 100.f);
    ASC->ApplyGameplayEffectToSelf(GetDefault<UWarStrikeCostEffect>(), 1.f, ASC->MakeEffectContext());
    TestEqual(TEXT("Cost is a real GAS attribute modifier"), State->GetAttributes()->GetMana(), 90.f);
    const UWarStrikeAbility* Ability = GetDefault<UWarStrikeAbility>();
    FGameplayEffectSpecHandle Cooldown = ASC->MakeOutgoingSpec(UWarStrikeCooldownEffect::StaticClass(), 1.f, ASC->MakeEffectContext());
    Cooldown.Data->DynamicGrantedTags.AppendTags(*Ability->GetCooldownTags());
    ASC->ApplyGameplayEffectSpecToSelf(*Cooldown.Data.Get());
    ASC->InitAbilityActorInfo(State, SecondAvatar);
    TestEqual(TEXT("ASC owner survives replacement"), ASC->GetOwnerActor(), static_cast<AActor*>(State));
    TestEqual(TEXT("ASC avatar is replaced"), ASC->GetAvatarActor(), SecondAvatar);
    TestTrue(TEXT("Cooldown survives avatar replacement"), ASC->HasAnyMatchingGameplayTags(*Ability->GetCooldownTags()));
    TestEqual(TEXT("Avatar replacement does not initialize resources by itself"), State->GetAttributes()->GetMana(), 90.f);
    for (int32 Index = 0; Index < 6; ++Index)
        ASC->ApplyGameplayEffectToSelf(GetDefault<UWarStrikeDamageEffect>(), 1.f, ASC->MakeEffectContext());
    TestEqual(TEXT("Overkill clamps health to zero"), State->GetAttributes()->GetHealth(), 0.f);
    World->EndPlay(EEndPlayReason::Quit);
    GEngine->DestroyWorldContext(World);
    World->DestroyWorld(false);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSpawnFailureTest, "AegisWar.Foundation.SpawnFailureReporting",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarSpawnFailureTest::RunTest(const FString& Parameters)
{
    if (!TestNotNull(TEXT("Engine is available for spawn test"), GEngine)) return false;
    const UWorld::InitializationValues Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Test world"), World)) return false;
    FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
    Context.SetCurrentWorld(World);
    AWarGameMode* Mode = World->SpawnActor<AWarGameMode>();
    AWarPlayerController* MissingStartPlayer = World->SpawnActor<AWarPlayerController>();
    AddExpectedError(TEXT("Player entry refused: This map has no valid PlayerStart"), EAutomationExpectedErrorFlags::Contains, 1);
    Mode->RestartPlayerAtPlayerStart(MissingStartPlayer, nullptr);
    TestTrue(TEXT("Missing player start reports an actionable entry error"), MissingStartPlayer->GetEntryFailure().ToString().Contains(TEXT("PlayerStart")));
    TestNull(TEXT("Failed entry has no invisible combatant"), MissingStartPlayer->GetPawn());
    AWarPlayerController* FailedPlayer = World->SpawnActor<AWarPlayerController>();
    AddExpectedError(TEXT("Player entry refused: Character entry failed"), EAutomationExpectedErrorFlags::Contains, 1);
    Mode->FailedToRestartPlayer(FailedPlayer);
    TestTrue(TEXT("The generic engine restart failure is surfaced"), FailedPlayer->GetEntryFailure().ToString().Contains(TEXT("entry failed")));
    TestNull(TEXT("Restart failure leaves no pawn"), FailedPlayer->GetPawn());
    World->DestroyWorld(false);
    GEngine->DestroyWorldContext(World);
    return true;
}

#endif
