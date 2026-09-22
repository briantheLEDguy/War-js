#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "WarAbilityCatalog.h"
#include "WarCombatStatus.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarGameplayEffects.h"
#include "AbilitySystemComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarClassAbilityTest, "AegisWar.Foundation.ClassAbilityCatalog",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarClassAbilityTest::RunTest(const FString& Parameters)
{
    FString Json, Error; TSharedPtr<FJsonObject> Manifest;
    if (!TestTrue(TEXT("Staged catalog exists"), FFileHelper::LoadFileToString(Json, *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/content.json"))))
        || !TestTrue(TEXT("Catalog is JSON"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Manifest))) return false;
    TArray<FWarAbilityDefinition> Abilities;
    if (!TestTrue(*Error, WarAbilities::Parse(Manifest, Abilities, Error))) return false;
    TestEqual(TEXT("All original class abilities present"), Abilities.Num(), 240);
    TSet<FName> Careers; int32 Unavailable = 0, Prelate = 0, Starter = 0;
    for (const auto& A : Abilities)
    {
        Careers.Add(A.Career); Unavailable += !A.UnavailableReason.IsEmpty();
        if (A.Effects.ContainsByPredicate([](const auto& E) { return E.Kind == TEXT("cleanse"); }))
            TestFalse(TEXT("Source cleanse exceptions remain usable while silenced"), A.bBlockedBySilence);
        TestTrue(TEXT("Finite nonnegative cost and bounded range"), FMath::IsFinite(A.Mana) && A.Mana >= 0 && A.Range >= 0 && A.Range <= 5000);
        if (A.Career != TEXT("battle_prelate")) continue;
        ++Prelate; Starter += A.UnlockLevel == 1;
        TestEqual(TEXT("Every Prelate ability has a visible verified hammer gesture"), WarAbilities::Motion(A, TEXT("civic_battle_prelate_m")), FName(TEXT("attack_melee")));
        if (A.Slot == 0) { TestEqual(TEXT("Litany builds Zeal"), WarAbilities::ResourceAfter(A, 20), 32.f); TestEqual(TEXT("Starter has no mana cost"), A.Mana, 0.f); }
        if (A.Slot == 3) { TestEqual(TEXT("Penance movement parsed"), A.Effects.Last().Direction, FName(TEXT("toward_target"))); TestEqual(TEXT("Travel in centimeters"), A.Effects.Last().Distance, 1200.f); }
        if (A.Slot == 9) TestEqual(TEXT("Finisher consumes all Zeal"), WarAbilities::ResourceAfter(A, 80), 0.f);
        if (A.Slot == 2) TestEqual(TEXT("Unreviewed Prelate variants retain their own cast role"), WarAbilities::Motion(A, TEXT("civic_battle_prelate_f")), FName(TEXT("cast")));
        if (A.Slot == 0)
        {
            TestEqual(TEXT("Measured supplied hammer contact"), WarAbilities::ReleaseFraction(A, TEXT("civic_battle_prelate_m")), .8f);
            TestEqual(TEXT("Contact timing is not copied to another character rig"), WarAbilities::ReleaseFraction(A, TEXT("civic_battle_prelate_f")), A.ReleaseFraction);
        }
    }
    TestEqual(TEXT("All 24 careers"), Careers.Num(), 24); TestEqual(TEXT("Only the three source-unimplemented summons disabled"), Unavailable, 3);
    TestEqual(TEXT("Full Prelate kit"), Prelate, 10); TestEqual(TEXT("Progression retains three starters"), Starter, 3);
    FWarAbilityEffect Amount; Amount.Minimum = 10; Amount.Maximum = 20; Amount.StatScale = .5; Amount.LevelScale = 2; Amount.ResourceScale = .1f;
    TestEqual(TEXT("Damage combines strength, level and spent resource once"), WarAbilities::Amount(Amount, 10, 3, 20, .5), 28.f);
    const auto Source = Manifest->GetObjectField(TEXT("abilities")); const auto Kit = Source->GetArrayField(TEXT("kits"))[0]->AsObject();
    auto Rows = Kit->GetArrayField(TEXT("abilities")); const auto Duplicate = Rows[0]; Rows.Add(Duplicate); Kit->SetArrayField(TEXT("abilities"), Rows);
    TestFalse(TEXT("Duplicate IDs/slots fail closed"), WarAbilities::Parse(Manifest, Abilities, Error));
    TestTrue(TEXT("No partially valid catalog published"), Abilities.IsEmpty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatStatusTest, "AegisWar.Foundation.ClassCombatStatus",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCombatStatusTest::RunTest(const FString& Parameters)
{
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!World) return false;
    auto& Context = GEngine->CreateNewWorldContext(EWorldType::Game); Context.SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());
    auto* Pawn = World->SpawnActor<AWarCharacter>(); auto* Status = UWarCombatStatus::On(Pawn);
    if (!TestNotNull(TEXT("Player has replicated status component"), Status)) { World->DestroyWorld(false); return false; }
    FWarAbilityEffect Effect; Effect.StatusKind = TEXT("guard"); Effect.Duration = 5; Effect.Magnitude = .25;
    Status->Apply(Effect, TEXT("guard_a"), Pawn, 10, 1); Status->Apply(Effect, TEXT("guard_b"), Pawn, 10, 1);
    TestEqual(TEXT("Guard uses strongest instead of stacking reduction"), Status->ReceiveDamage(100), 75.f);
    Effect.StatusKind = TEXT("empower"); Effect.Magnitude = .2f; Status->Apply(Effect, TEXT("power"), Pawn, 10, 1);
    TestEqual(TEXT("Outgoing empower"), Status->OutgoingScale(), 1.2f);
    Effect.StatusKind = TEXT("root"); Status->Apply(Effect, TEXT("root"), Pawn, 10, 1);
    TestEqual(TEXT("Root prevents locomotion"), Status->MovementScale(), 0.f);
    Status->Cleanse({TEXT("root")}); TestFalse(TEXT("Cleanse removes root"), Status->Has(TEXT("root")));
    TestTrue(TEXT("Cleanse preserves beneficial guard"), Status->Has(TEXT("guard")));
    Status->Clear(); TestEqual(TEXT("Death/respawn clears all status modifiers"), Status->OutgoingScale(), 1.f);
    auto* State = World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
    auto* ASC = State->GetAbilitySystemComponent(); ASC->InitAbilityActorInfo(State, Pawn);
    ASC->ApplyGameplayEffectToSelf(GetDefault<UWarInitialAttributesEffect>(), 1, ASC->MakeEffectContext());
    Effect.StatusKind = TEXT("shield"); Effect.Magnitude = .25f;
    Status->Apply(Effect, TEXT("shield_a"), Pawn, 10, 1); Status->Apply(Effect, TEXT("shield_b"), Pawn, 10, 1);
    TestEqual(TEXT("Shield is one strongest pool, not additive"), Status->ReceiveDamage(40), 15.f);
    Status->Clear(); Effect.Magnitude = .6f; Status->Apply(Effect, TEXT("shield"), Pawn, 10, 1);
    auto Damage = ASC->MakeOutgoingSpec(UWarEnemyDamageEffect::StaticClass(), 1, ASC->MakeEffectContext());
    Damage.Data->SetSetByCallerMagnitude(FName(TEXT("WarEnemyDamage")), -120);
    ASC->ApplyGameplayEffectSpecToSelf(*Damage.Data.Get());
    TestEqual(TEXT("Shield mitigates before health clamp, including raw overkill"), State->GetAttributes()->GetHealth(), 40.f);
    TestFalse(TEXT("Raw overkill cannot bypass a sufficient shield"), Pawn->IsDead());
    Effect.StatusKind = TEXT("slow"); Effect.Magnitude = .4f; Effect.Duration = .1f; Status->Apply(Effect, TEXT("slow"), Pawn, 10, 1);
    TestEqual(TEXT("Slow affects speed"), Status->MovementScale(), .6f);
    World->Tick(LEVELTICK_All, .2f);
    TestEqual(TEXT("Expired slow restores movement"), Status->MovementScale(), 1.f);
    World->EndPlay(EEndPlayReason::Quit); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); return true;
}
#endif
