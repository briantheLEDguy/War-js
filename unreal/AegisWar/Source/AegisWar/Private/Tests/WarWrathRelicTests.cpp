#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWrathRelic.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCombatStatus.h"
#include "WarGameplayEffects.h"
#include "WarSiegeGameMode.h"
#include "AbilitySystemComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWrathRelicTest, "AegisWar.Foundation.IconOfWrath",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarWrathRelicTest::RunTest(const FString& Parameters)
{
    const auto Values=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false).CreateAISystem(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    if (!World) return false;
    auto& Context=GEngine->CreateNewWorldContext(EWorldType::Game); Context.SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());
    World->BeginPlay();
    World->GetWorldSettings()->NotifyBeginPlay();
    const auto Box=[&](FVector Center,FVector Extent)
    {
        auto* Actor=World->SpawnActor<AActor>(); auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->SetRootComponent(Shape); Shape->SetBoxExtent(Extent); Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Shape->SetCollisionObjectType(ECC_WorldStatic); Shape->SetCollisionResponseToAllChannels(ECR_Block);
        Shape->RegisterComponent(); Actor->SetActorLocation(Center); return Actor;
    };
    Box(FVector(0,0,-10),FVector(2000,2000,10));
    const auto Spawn=[&](float X,EWarRealm Realm,EWarSiegeUnit Unit=EWarSiegeUnit::Participant)
    {
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=World->SpawnActor<AWarSiegeCharacter>(FVector(X,0,100),FRotator::ZeroRotator,Params); Pawn->Unit=Unit;
        auto* Controller=World->SpawnActor<AAIController>(); Controller->Possess(Pawn);
        auto* State=World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        auto* ASC=State->GetAbilitySystemComponent(); ASC->InitAbilityActorInfo(State,Pawn);
        ASC->ApplyGameplayEffectToSelf(GetDefault<UWarInitialAttributesEffect>(),1,ASC->MakeEffectContext());
        Pawn->GetCharacterMovement()->DisableMovement(); return Pawn;
    };
    auto* Caster=Spawn(0,EWarRealm::Aegis); auto* CasterTwo=Spawn(-150,EWarRealm::Aegis);
    auto* Dealer=Spawn(150,EWarRealm::Aegis); auto* Victim=Spawn(320,EWarRealm::Riftbound);
    auto* Encounter=Spawn(150,EWarRealm::Aegis,EWarSiegeUnit::Guard);
    Encounter->SetActorLocation(FVector(150,200,100));
    const auto Health=[](AWarCharacter* Pawn) { return Pawn->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth(); };
    const auto SetHealth=[](AWarCharacter* Pawn,float Value) { Pawn->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),Value); };
    const auto Damage=[&](AWarCharacter* From,AWarCharacter* To,float Amount)
    {
        auto* ASC=To->GetAbilitySystemComponent(); auto EffectContext=ASC->MakeEffectContext(); EffectContext.AddInstigator(From,From);
        auto Spec=ASC->MakeOutgoingSpec(UWarEnemyDamageEffect::StaticClass(),1,EffectContext);
        Spec.Data->SetSetByCallerMagnitude(FName(TEXT("WarEnemyDamage")),-Amount); ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
    };
    const auto Count=[&]() { int32 N=0; for (TActorIterator<AWarWrathRelic> It(World);It;++It) if (!It->IsActorBeingDestroyed()) ++N; return N; };
    FString Error; FVector Position;
    TestTrue(*Error,AWarWrathRelic::Placement(Caster,Position,Error));
    TestTrue(*Error,AWarWrathRelic::Place(Caster,Error));
    TestTrue(TEXT("One relic can be replaced"),AWarWrathRelic::Place(Caster,Error));
    TestEqual(TEXT("Replacement removes the previous actor"),Count(),1);
    SetHealth(Dealer,40); SetHealth(Victim,50); Damage(Dealer,Victim,20);
    TestEqual(TEXT("Actual hostile health damage heals its dealer"),Health(Dealer),42.f);
    TestTrue(TEXT("Second allied caster may place an overlapping field"),AWarWrathRelic::Place(CasterTwo,Error));
    Damage(Dealer,Victim,10); TestEqual(TEXT("Overlapping relics do not stack"),Health(Dealer),43.f);
    SetHealth(Encounter,40); Damage(Encounter,Victim,10); TestEqual(TEXT("Encounter NPCs cannot receive relic healing"),Health(Encounter),40.f);
    SetHealth(Dealer,99); Damage(Dealer,Victim,1000);
    TestEqual(TEXT("Overkill counts only remaining hostile health and healing clamps at maximum"),Health(Dealer),100.f);
    auto* FreshVictim=Spawn(450,EWarRealm::Riftbound);
    SetHealth(Dealer,40);
    FWarAbilityEffect Guard; Guard.StatusKind=TEXT("guard"); Guard.Duration=5; Guard.Magnitude=.5f;
    UWarCombatStatus::On(FreshVictim)->Apply(Guard,TEXT("test_guard"),FreshVictim,10,1);
    Damage(Dealer,FreshVictim,40); TestEqual(TEXT("Guarded damage procs on post-mitigation health loss"),Health(Dealer),42.f);
    SetHealth(CasterTwo,100); Damage(Dealer,CasterTwo,20); TestEqual(TEXT("Friendly health damage never procs"),Health(Dealer),42.f);
    Dealer->SetActorLocation(FVector(950,0,100)); Damage(Dealer,FreshVictim,20);
    TestEqual(TEXT("Outside five metres cannot proc"),Health(Dealer),42.f);
    Dealer->SetActorLocation(FVector(250,0,100));
    auto* Wall=Box(FVector(110,0,150),FVector(15,200,150)); Damage(Dealer,FreshVictim,20);
    TestEqual(TEXT("Opaque wall blocks both overlapping relics"),Health(Dealer),42.f); Wall->Destroy();
    Caster->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
    CasterTwo->GetController()->UnPossess(); ++GFrameCounter; World->Tick(LEVELTICK_All,.1f);
    TestEqual(TEXT("Zone exit and disconnect remove owned fields"),Count(),0);
    Caster->GetPlayerState<AWarPlayerState>()->SetCurrentZoneTrusted(TEXT("aegis_capital"));
    TestTrue(TEXT("Can place again after returning"),AWarWrathRelic::Place(Caster,Error));
    for (int32 Frame=0;Frame<110;++Frame) { ++GFrameCounter; World->Tick(LEVELTICK_All,.1f); }
    TestEqual(TEXT("Relic lasts ten seconds"),Count(),0);
    TestTrue(TEXT("Death cleanup fixture placed"),AWarWrathRelic::Place(Caster,Error)); Caster->HandleDeath();
    TestEqual(TEXT("Caster death immediately removes its relic"),Count(),0);
    TestFalse(TEXT("Dead casters cannot place relics"),AWarWrathRelic::Place(Caster,Error));
    World->EndPlay(EEndPlayReason::Quit); GEngine->DestroyWorldContext(World); World->DestroyWorld(false);
    return true;
}
#endif
