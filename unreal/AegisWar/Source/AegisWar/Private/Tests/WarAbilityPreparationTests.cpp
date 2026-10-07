#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarAbilityRuntime.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityPreparationTest,"AegisWar.Foundation.AbilityStationaryPreparation",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarAbilityPreparationTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Controller=World->SpawnActor<AWarPlayerController>();auto* State=World->SpawnActor<AWarPlayerState>();
    auto* Pawn=World->SpawnActor<AWarCharacter>();Controller->PlayerState=State;State->SetOwner(Controller);
    Controller->Possess(Pawn);Pawn->SetPlayerState(State);
    // Eligibility-only fixture: no renderer, visual acceptance or ability effects are exercised.
    Pawn->VisualDefinition=NewObject<UWarCharacterVisualDefinition>();Pawn->VisualDefinition->ClassId=TEXT("sunfire_templar");Pawn->bVisualReady=true;
    State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),0);
    auto* Runtime=State->GetClassAbilities();Runtime->Career=Pawn->GetCareerId();Runtime->Resource=0;Runtime->bMovementIntent=true;
    FWarAbilityDefinition Ability;Ability.Career=Runtime->Career;Ability.Id=TEXT("sunfire_templar.preparation_test");
    Ability.TimingMode=TEXT("cast");Ability.bCancelOnMovement=true;Ability.UnlockLevel=0;Ability.Mana=20;
    FString Error;const auto Position=Pawn->GetActorLocation();const auto Serial=Runtime->GetActionSerial();
    TestFalse(TEXT("Ordinary activation still requires stopping"),Runtime->CanActivate(Ability,Pawn,Error));
    TestTrue(TEXT("Ordinary movement validation is retained"),Error.Contains(TEXT("Stop moving")));
    TestFalse(TEXT("Advisory cannot stop for an unaffordable cast"),Runtime->CanPrepareStationaryCast(Ability,Pawn,Error));
    TestTrue(TEXT("Advisory reaches actual mana validation without changing locomotion"),Error.Contains(TEXT("mana")));
    Ability.Mana=0;Ability.Cost=10;
    TestFalse(TEXT("Class resource remains required before preparing"),Runtime->CanPrepareStationaryCast(Ability,Pawn,Error));
    TestTrue(TEXT("Resource failure is preserved"),Error.Contains(TEXT("Requires")));
    Ability.Cost=0;Ability.TargetKind=TEXT("ground");
    TestFalse(TEXT("A missing ground point cannot cause a stop then failed cast"),Runtime->CanPrepareStationaryCast(Ability,Pawn,Error));
    TestTrue(TEXT("Unsupported ground preparation is explicit"),Error.Contains(TEXT("ground point")));
    // Read an installed supplied clip's duration; never equip or play it here.
    auto* Clip=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Characters/AnimationReplacement/9c920bf8344f/civic_sunfire_templar_m/Clips/New_spell_ritual_mixamo_com.New_spell_ritual_mixamo_com"));
    if (!TestNotNull(TEXT("Installed character-specific supplied presentation exists"),Clip)) return false;
    TestTrue(TEXT("Positive eligibility has a real nonzero presentation duration"),Clip->GetPlayLength()>0);
    Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    Pawn->VisualDefinition->ImportedAnimations.Add(TEXT("cast"),Clip);Ability.TargetKind=TEXT("self");
    const bool Prepared=Runtime->CanPrepareStationaryCast(Ability,Pawn,Error);
    TestTrue(*FString::Printf(TEXT("A fully eligible moving caster can prepare without stopping yet: %s"),*Error),Prepared);
    TestFalse(TEXT("Ordinary activation of the same eligible definition still rejects movement"),Runtime->CanActivate(Ability,Pawn,Error));
    TestTrue(TEXT("Actual movement remains part of authoritative eligibility"),Error.Contains(TEXT("Stop moving")));
    TestTrue(TEXT("Advisory calls never cancel movement or create an action"),Runtime->HasMovementIntent() && Runtime->GetActionSerial()==Serial);
    TestTrue(TEXT("Advisory never moves the avatar"),Pawn->GetActorLocation().Equals(Position,0));
    TestFalse(TEXT("Advisory never begins a cast"),Runtime->IsStationaryCast());
    return !HasAnyErrors();
}
#endif
