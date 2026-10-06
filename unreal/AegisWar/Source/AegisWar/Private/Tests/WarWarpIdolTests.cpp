#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWarpIdol.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCombatStatus.h"
#include "WarGameplayEffects.h"
#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.h"
#include "AbilitySystemComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWarpIdolTest, "AegisWar.Foundation.WarpIdol",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarWarpIdolTest::RunTest(const FString& Parameters)
{
    const auto Values=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    if (!World) return false;
    auto& Context=GEngine->CreateNewWorldContext(EWorldType::Game); Context.SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL()); World->BeginPlay(); World->GetWorldSettings()->NotifyBeginPlay();
    const auto Box=[&](FVector Center,FVector Extent)
    {
        auto* Actor=World->SpawnActor<AActor>(); auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->SetRootComponent(Shape); Shape->SetBoxExtent(Extent); Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Shape->SetCollisionObjectType(ECC_WorldStatic); Shape->SetCollisionResponseToAllChannels(ECR_Block);
        Shape->RegisterComponent(); Actor->SetActorLocation(Center); return Actor;
    };
    Box(FVector(0,0,-10),FVector(5000,5000,10));
    const auto Spawn=[&](FVector Position,EWarRealm Realm)
    {
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=World->SpawnActor<AWarSiegeCharacter>(Position,FRotator::ZeroRotator,Params);
        auto* Controller=World->SpawnActor<AAIController>(); Controller->Possess(Pawn);
        auto* State=World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        auto* ASC=State->GetAbilitySystemComponent(); ASC->InitAbilityActorInfo(State,Pawn);
        ASC->ApplyGameplayEffectToSelf(GetDefault<UWarInitialAttributesEffect>(),1,ASC->MakeEffectContext());
        const TCHAR* Path=Realm==EWarRealm::Riftbound ? TEXT("/Game/Characters/SiegeStaging/Visual_riven_void_magister_m") : TEXT("/Game/MigrationProof/Visual_civic_battle_prelate_m");
        FString Error; TestTrue(TEXT("Authored test combatant visual is ready"),Pawn->SetVisualDefinition(LoadObject<UWarCharacterVisualDefinition>(nullptr,Path),Error));
        Pawn->GetCharacterMovement()->DisableMovement(); return Pawn;
    };
    auto* Caster=Spawn(FVector(0,0,100),EWarRealm::Riftbound);
    auto* Ally=Spawn(FVector(250,150,100),EWarRealm::Riftbound);
    auto* Enemy=Spawn(FVector(450,0,100),EWarRealm::Aegis);
    auto* FarEnemy=Spawn(FVector(700,200,100),EWarRealm::Aegis);
    const auto Health=[](AWarCharacter* P) { return P->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth(); };
    const auto Advance=[&](float Seconds) { for (int32 I=0;I<FMath::CeilToInt(Seconds*10);++I) { ++GFrameCounter; World->Tick(LEVELTICK_All,.1f); } };
    const auto Count=[&]() { int32 N=0; for (TActorIterator<AWarWarpIdol> It(World);It;++It) if (!It->IsActorBeingDestroyed()) ++N; return N; };
    const auto Current=[&]() { for (TActorIterator<AWarWarpIdol> It(World);It;++It) if (!It->IsActorBeingDestroyed()) return *It; return static_cast<AWarWarpIdol*>(nullptr); };
    FString Error; FVector Position;
    TestTrue(TEXT("Grounded clear authored placement"),AWarWarpIdol::Placement(Caster,Position,Error));
    auto* Wall=Box(FVector(75,0,150),FVector(10,100,150));
    TestFalse(TEXT("Cannot place through a wall"),AWarWarpIdol::Place(Caster,10,Error)); Wall->Destroy();
    Wall=Box(FVector(190,0,90),FVector(20,50,80));
    TestFalse(TEXT("Authored idol bounds cannot overlap an obstacle"),AWarWarpIdol::Place(Caster,10,Error)); Wall->Destroy();
    Caster->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    TestFalse(TEXT("Cannot place while airborne"),AWarWarpIdol::Place(Caster,10,Error)); Caster->GetCharacterMovement()->DisableMovement();
    TestFalse(TEXT("Zero pulse damage rejected"),AWarWarpIdol::Place(Caster,0,Error));
    TestTrue(TEXT("Place authored idol"),AWarWarpIdol::Place(Caster,10,Error));
    TestTrue(TEXT("Replacement succeeds"),AWarWarpIdol::Place(Caster,10,Error));
    TestEqual(TEXT("One idol per owner"),Count(),1);
    if (auto* Idol=Current())
    {
        TestFalse(TEXT("Allies are never targets"),Idol->CanAttack(Ally));
        TestTrue(TEXT("Nearby hostile is eligible"),Idol->CanAttack(Enemy));
        Advance(2.2f); TestEqual(TEXT("Nearest hostile takes one pulse"),Health(Enemy),90.f);
        TestEqual(TEXT("Other hostile is untouched"),Health(FarEnemy),100.f); TestEqual(TEXT("Ally untouched"),Health(Ally),100.f);
        FWarAbilityEffect Feed; Feed.StatusKind=TEXT("empower"); Feed.Duration=8; Feed.Magnitude=.2f;
        UWarCombatStatus::On(Caster)->Apply(Feed,TEXT("void_magister.feed_the_idol"),Caster,10,1);
        Advance(2.1f); TestEqual(TEXT("Feed the Idol boosts live pulse damage once"),Health(Enemy),78.f);
        Wall=Box(FVector(320,0,150),FVector(10,1000,150)); Advance(2.1f);
        TestEqual(TEXT("Idol sight cannot cross walls"),Health(Enemy),78.f); Wall->Destroy();
        Enemy->SetActorLocation(FVector(1800,0,100)); TestFalse(TEXT("Idol range measured from its own position"),Idol->CanAttack(Enemy));
        Enemy->SetActorLocation(FVector(450,0,100));
        Enemy->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
        TestFalse(TEXT("Other zones excluded"),Idol->CanAttack(Enemy));
        Enemy->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        Idol->SetActorTickEnabled(false); Advance(7); UWarCombatStatus::On(Caster)->Clear();
        Idol->Tick(7); TestEqual(TEXT("A delayed tick causes only one pulse"),Health(Enemy),68.f);
        Idol->Tick(7); TestEqual(TEXT("Missed pulses are not caught up"),Health(Enemy),68.f); Idol->SetActorTickEnabled(true);
        Caster->SetActorLocation(FVector(-2200,0,100)); Advance(.2f); TestEqual(TEXT("Leaving owner leash removes idol"),Count(),0);
    }
    Caster->SetActorLocation(FVector(0,0,100));
    TestTrue(TEXT("Place before zone change"),AWarWarpIdol::Place(Caster,1,Error));
    Caster->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("dawnline_expanse")); Advance(.2f);
    TestEqual(TEXT("Changing zone removes idol"),Count(),0); Caster->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("aegis_capital"));
    TestTrue(TEXT("Place before disconnect"),AWarWarpIdol::Place(Caster,1,Error));
    auto* Controller=Caster->GetController(); auto* OwnerState=Caster->GetPlayerState<AWarPlayerState>();
    Controller->UnPossess(); Advance(.2f);
    TestEqual(TEXT("Disconnect removes idol"),Count(),0); Controller->Possess(Caster); Caster->SetPlayerState(OwnerState);
    TestTrue(TEXT("Place expiry fixture"),AWarWarpIdol::Place(Caster,1,Error)); Advance(30.2f);
    TestEqual(TEXT("Thirty second lifetime"),Count(),0);
    TestTrue(TEXT("Place death fixture"),AWarWarpIdol::Place(Caster,1,Error)); Caster->HandleDeath();
    TestEqual(TEXT("Death immediately removes idol"),Count(),0);
    TestFalse(TEXT("Dead caster cannot place"),AWarWarpIdol::Place(Caster,1,Error));
    World->EndPlay(EEndPlayReason::Quit); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); return true;
}
#endif
