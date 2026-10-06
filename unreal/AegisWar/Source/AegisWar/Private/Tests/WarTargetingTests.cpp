#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarEnemy.h"
#include "WarContentSubsystem.h"
#include "WarTargetReticle.h"
#include "WarOverheadHealth.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarTargetingTest, "AegisWar.Foundation.TargetSelection",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarTargetingTest::RunTest(const FString& Parameters)
{
    auto* Instance = NewObject<UGameInstance>(GEngine); Instance->AddToRoot(); Instance->InitializeStandalone();
    auto* World = Instance->GetWorld();
    World->InitializeActorsForPlay(FURL()); World->BeginPlay(); World->GetWorldSettings()->NotifyBeginPlay();
    auto* PC = World->SpawnActor<AWarPlayerController>();
    const auto Spawn = [&](FVector Position, bool bEnemy)
    {
        auto* Visual = LoadObject<UWarCharacterVisualDefinition>(nullptr, bEnemy
            ? TEXT("/Game/Characters/SiegeStaging/Visual_riven_void_magister_m")
            : TEXT("/Game/MigrationProof/Visual_civic_battle_prelate_m"));
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn = World->SpawnActor<AWarCharacter>(Position, FRotator::ZeroRotator, Params);
        auto* State = World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(bEnemy ? EWarRealm::Riftbound : EWarRealm::Aegis);
        State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        FString Error; TestTrue(TEXT("Authored character fixture loads"), Pawn->SetVisualDefinition(Visual, Error));
        State->InitializeForPawn(Pawn);
        return Pawn;
    };
    auto* Self = Spawn(FVector(0, 0, 100), false);
    PC->PlayerState = Self->GetPlayerState(); PC->Possess(Self); PC->SetViewTarget(Self);
    auto* Ally = Spawn(FVector(200, 300, 100), false);
    auto* Near = Spawn(FVector(700, -300, 100), true);
    auto* Far = Spawn(FVector(1300, 400, 100), true);
    FWarOverheadHealth Bar;
    TestTrue(TEXT("Unselected full-health ally has a default overhead bar"), WarOverheadHealth::Read(PC, Ally, Bar));
    TestFalse(TEXT("Allied overhead bar uses friendly color"), Bar.bEnemy);
    TestTrue(TEXT("Unselected enemy has a default overhead bar"), WarOverheadHealth::Read(PC, Near, Bar));
    TestTrue(TEXT("Hostile overhead bar uses enemy color"), Bar.bEnemy);
    auto* Vitals = Ally->GetPlayerState<AWarPlayerState>()->GetAbilitySystemComponent();
    Vitals->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(), 200);
    Vitals->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), 50);
    TestTrue(TEXT("Damaged ally remains visible without local hit events"), WarOverheadHealth::Read(PC, Ally, Bar));
    TestEqual(TEXT("Bar follows current health immediately"), Bar.Fraction, .25f);
    Vitals->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), 150);
    WarOverheadHealth::Read(PC, Ally, Bar);
    TestEqual(TEXT("Healing immediately refills overhead bar"), Bar.Fraction, .75f);
    Vitals->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(), 300);
    WarOverheadHealth::Read(PC, Ally, Bar);
    TestEqual(TEXT("Maximum-health changes update proportion"), Bar.Fraction, .5f);
    Vitals->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), 0);
    TestFalse(TEXT("Zero replicated health hides bar before death notification"), WarOverheadHealth::Read(PC, Ally, Bar));
    Vitals->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), 300);
    TestFalse(TEXT("Local player keeps existing HUD vitals only"), WarOverheadHealth::Read(PC, Self, Bar));
    // Recreate the installed NPC binding; production must still reject missing or substituted models.
    FString WorldVisualJson, VisualError; TMap<FString, FWarWorldVisualBinding> Bindings;
    TestTrue(TEXT("Reviewed world visual catalog available"), FFileHelper::LoadFileToString(WorldVisualJson,
        *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/world-visuals.json"))));
    TestTrue(TEXT("Reviewed world visual catalog matches content"), WarWorldVisuals::Parse(WorldVisualJson,
        Instance->GetSubsystem<UWarContentSubsystem>()->GetSummary().SourceSha256, Bindings, VisualError));
    const auto* Binding = Bindings.Find(WarWorldVisuals::Key(TEXT("training_dummy"), TEXT("aegis_capital"), TEXT("aegis_capital_training_dummy_1")));
    if (TestNotNull(TEXT("Authored training NPC binding"), Binding))
    {
        const FTransform NpcTransform(FVector(350, 1000, 100));
        auto* Npc = World->SpawnActorDeferred<AWarEnemy>(AWarEnemy::StaticClass(), NpcTransform, nullptr, nullptr,
            ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        Npc->ZoneId = Binding->Zone; Npc->EnemyId = Binding->Entity;
        Npc->TrainingMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, *Binding->Mesh));
        for (int32 I = 0; I < Binding->Materials.Num(); ++I)
            Npc->TrainingMesh->SetMaterial(I, LoadObject<UMaterialInterface>(nullptr, *Binding->Materials[I]));
        Npc->TrainingMesh->SetCollisionProfileName(Binding->CollisionProfile);
        Npc->FinishSpawning(NpcTransform);
        TestTrue(TEXT("Authored NPC health bar available by default"), WarOverheadHealth::Read(PC, Npc, Bar));
        TestTrue(TEXT("Damageable NPC uses hostile color"), Bar.bEnemy);
        TestTrue(TEXT("NPC accepts actual authoritative damage"), Npc->ReceiveAbilityDamage(Self, Npc->GetDefinition().MaxHealth * .5f, 3000, false));
        WarOverheadHealth::Read(PC, Npc, Bar);
        TestEqual(TEXT("NPC overhead fill follows effective damage"), Bar.Fraction, .5f);
        Npc->Destroy();
    }
    TestTrue(TEXT("Cursor visible on controller creation"), PC->bShowMouseCursor);
    PC->bShowMouseCursor = false; PC->RestoreGameplayInput();
    TestTrue(TEXT("Gameplay restoration always shows cursor"), PC->bShowMouseCursor);
    TestFalse(TEXT("Self is not a target"), PC->SelectCombatTarget(Self));
    TestTrue(TEXT("Allies remain directly selectable"), PC->SelectCombatTarget(Ally));
    TestFalse(TEXT("Ally is not hostile"), PC->IsEnemyCombatTarget(Ally));
    PC->CycleCombatTarget(); TestEqual(TEXT("Tab from ally starts at nearest enemy"), PC->GetCombatTarget(), static_cast<AActor*>(Near));
    PC->CycleCombatTarget(); TestEqual(TEXT("Tab advances to other enemy"), PC->GetCombatTarget(), static_cast<AActor*>(Far));
    PC->CycleCombatTarget(); TestEqual(TEXT("Tab wraps without selecting ally"), PC->GetCombatTarget(), static_cast<AActor*>(Near));
    PC->SelectCombatTarget(Far); PC->TargetNearestEnemy();
    TestEqual(TEXT("Nearest ignores current selection"), PC->GetCombatTarget(), static_cast<AActor*>(Near));
    PC->TargetNearestEnemy(); TestEqual(TEXT("Nearest never cycles"), PC->GetCombatTarget(), static_cast<AActor*>(Near));
    Near->SetActorHiddenInGame(true); PC->TargetNearestEnemy();
    TestFalse(TEXT("Hidden character has no overhead bar"), WarOverheadHealth::Read(PC, Near, Bar));
    TestEqual(TEXT("Hidden enemies excluded"), PC->GetCombatTarget(), static_cast<AActor*>(Far));
    Near->SetActorHiddenInGame(false);
    Near->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("riftspire_capital")); PC->TargetNearestEnemy();
    TestFalse(TEXT("Other-zone character has no overhead bar"), WarOverheadHealth::Read(PC, Near, Bar));
    TestEqual(TEXT("Other zones excluded"), PC->GetCombatTarget(), static_cast<AActor*>(Far));
    Near->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("aegis_capital"));
    Near->SetActorLocation(FVector(6000, 0, 100)); PC->TargetNearestEnemy();
    TestFalse(TEXT("Out-of-range character has no overhead bar"), WarOverheadHealth::Read(PC, Near, Bar));
    TestEqual(TEXT("Enemies beyond selection range excluded"), PC->GetCombatTarget(), static_cast<AActor*>(Far));
    Near->SetActorLocation(FVector(700, -300, 100));
    PC->SetIgnoreMoveInput(true); PC->TargetNearestEnemy(); PC->CycleCombatTarget();
    TestFalse(TEXT("Modal blocks direct selection"), PC->SelectCombatTarget(Ally));
    TestEqual(TEXT("Modal preserves selection"), PC->GetCombatTarget(), static_cast<AActor*>(Far));
    PC->SetIgnoreMoveInput(false);
    auto* Wall = World->SpawnActor<AActor>(); auto* Box = NewObject<UBoxComponent>(Wall);
    Wall->SetRootComponent(Box); Box->SetBoxExtent(FVector(25, 2000, 2000));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->RegisterComponent(); Wall->SetActorLocation(FVector(400, 0, 100));
    TestFalse(TEXT("Click cannot select through wall"), PC->SelectCombatTarget(Near));
    PC->TargetNearestEnemy(); TestNull(TEXT("No visible enemies clears target"), PC->GetCombatTarget());
    Wall->Destroy();
    PC->TargetNearestEnemy(); Near->HandleDeath();
    TestFalse(TEXT("Dead character has no overhead bar"), WarOverheadHealth::Read(PC, Near, Bar));
    TestNull(TEXT("Dead selection is invalidated immediately"), PC->GetCombatTarget());
    PC->TargetNearestEnemy(); TestEqual(TEXT("Dead enemy skipped"), PC->GetCombatTarget(), static_cast<AActor*>(Far));
    auto* Unloaded = World->SpawnActor<AWarCharacter>();
    TestFalse(TEXT("Unloaded character has no overhead bar"), WarOverheadHealth::Read(PC, Unloaded, Bar));
    TestFalse(TEXT("Missing visual cannot become a target"), PC->SelectCombatTarget(Unloaded));
    PC->SelectCombatTarget(Ally); Near->Destroy(); Far->Destroy(); PC->CycleCombatTarget();
    TestNull(TEXT("Tab with only allies clears target"), PC->GetCombatTarget());
    PC->SelectCombatTarget(Ally); Ally->Destroy(); TestNull(TEXT("Destroyed selection is invalidated"), PC->GetCombatTarget());
    World->EndPlay(EEndPlayReason::Quit); Instance->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); Instance->RemoveFromRoot();
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarTargetReticleTest, "AegisWar.Foundation.TargetReticle",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarTargetReticleTest::RunTest(const FString& Parameters)
{
    const auto Friendly = WarTargetReticle::Color(false), Enemy = WarTargetReticle::Color(true);
    TestTrue(TEXT("Friendly reticle is blue"), Friendly.B > Friendly.R && Friendly.B > Friendly.G);
    TestTrue(TEXT("Enemy reticle is red"), Enemy.R > Enemy.B && Enemy.R > Enemy.G);
    const FBox2D Bounds(FVector2D(100, 200), FVector2D(200, 400));
    const auto Lines = WarTargetReticle::Corners(Bounds, 1);
    TestEqual(TEXT("Four open corners with two strokes each"), Lines.Num(), 8);
    for (const auto& Line : Lines)
    {
        TestTrue(TEXT("Corner strokes remain within target bounds"), Bounds.IsInsideOrOn(Line.Key) && Bounds.IsInsideOrOn(Line.Value));
        TestEqual(TEXT("Readable bounded stroke length"), FVector2D::Distance(Line.Key, Line.Value), 24.0);
    }
    const auto Tiny = WarTargetReticle::Corners(FBox2D(FVector2D(0), FVector2D(10, 10)), 1);
    TestEqual(TEXT("Distant target corners do not overlap"), FVector2D::Distance(Tiny[0].Key, Tiny[0].Value), 3.0);
    TestTrue(TEXT("Invalid projected bounds draw nothing"), WarTargetReticle::Corners(FBox2D(ForceInit), 1).IsEmpty());
    return true;
}
#endif
