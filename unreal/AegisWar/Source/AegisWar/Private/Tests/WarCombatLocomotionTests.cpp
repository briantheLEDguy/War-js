#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarAnimationInstance.h"
#include "WarPlayerState.h"
#include "WarAbilityRuntime.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "AIController.h"
#include "WarAnimationGameplayCapture.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatLocomotionTest,"AegisWar.Foundation.CombatLocomotion",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCombatLocomotionTest::RunTest(const FString& Parameters)
{
    auto* Instance=NewObject<UGameInstance>(GEngine); Instance->AddToRoot(); Instance->InitializeStandalone();
    auto* World=Instance->GetWorld(); World->InitializeActorsForPlay(FURL()); World->BeginPlay(); World->GetWorldSettings()->NotifyBeginPlay();
    FWarAnimationGameplayCapture Capture(World,TEXT("CombatFluidityCapture"));
    auto* Floor=World->SpawnActor<AActor>(); auto* Box=NewObject<UBoxComponent>(Floor); Floor->SetRootComponent(Box);
    Box->SetBoxExtent(FVector(5000,5000,20)); Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Box->SetCollisionObjectType(ECC_WorldStatic); Box->SetCollisionResponseToAllChannels(ECR_Block); Box->RegisterComponent(); Floor->SetActorLocation(FVector(0,0,-20));
    const auto Advance=[&] { ++GFrameCounter; World->Tick(LEVELTICK_All,1.f/60); };
    const TArray<FString> Profiles={TEXT("civic_battle_prelate_m"),TEXT("civic_sunfire_templar_m"),TEXT("mire_warbrute_m"),TEXT("civic_ember_arcanist_m"),TEXT("riven_ruin_oracle_m"),TEXT("riven_void_magister_m")};
    for (int32 Index=0;Index<Profiles.Num();++Index)
    {
        const FString Path=(Index<4 ? TEXT("/Game/MigrationProof/Visual_") : TEXT("/Game/Characters/SiegeStaging/Visual_"))+Profiles[Index];
        auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*Path);
        if (!TestNotNull(TEXT("Equipped profile"),Visual)) continue;
        auto* Pawn=World->SpawnActor<AWarCharacter>(FVector(0,0,99),FRotator::ZeroRotator);
        auto* Controller=World->SpawnActor<AAIController>(); Controller->Possess(Pawn);
        auto* State=World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State); State->SetDevelopmentRealm(Visual->Realm);
        State->SetCurrentZoneTrusted(TEXT("aegis_capital")); FString Error;
        TestTrue(TEXT("Equipped visual and split bone validate"),Pawn->SetVisualDefinition(Visual,Error)); State->InitializeForPawn(Pawn);
        Pawn->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Pawn->GetCharacterMovement()->bUseControllerDesiredRotation=false;
        for (const auto& Direction:TArray<TPair<FString,FVector>>{{TEXT("forward"),FVector(1,0,0)},{TEXT("strafe"),FVector(0,1,0)},{TEXT("backward"),FVector(-1,0,0)}})
        {
            Pawn->SetActorLocation(FVector(0,0,99)); Pawn->GetCharacterMovement()->StopMovementImmediately();
            Pawn->MulticastPlayAbilityMotion(TEXT("attack_melee"),Pawn->GetAbilityAnimationDuration(TEXT("attack_melee")),false);
            for (int Frame=0;Frame<20;++Frame) { Pawn->AddMovementInput(Direction.Value,1); Advance(); }
            const auto* Animation=CastChecked<UWarAnimationInstance>(Pawn->GetMesh()->GetAnimInstance());
            TestTrue(TEXT("Action retains moving lower body"),Animation->LocomotionWeight>.95f);
            TestTrue(TEXT("Combat does not stop capsule movement"),Pawn->GetActorLocation().Size2D()>20);
            TestTrue(TEXT("Locomotion clip is evaluated"),Animation->Locomotion!=nullptr && Animation->LocomotionTime>0);
            for (const FTransform& Bone:Pawn->GetMesh()->GetComponentSpaceTransforms()) TestFalse(TEXT("Finite layered pose"),Bone.ContainsNaN());
            TInlineComponentArray<UStaticMeshComponent*> Parts(Pawn);
            for (const auto* Part:Parts) if (Part->GetStaticMesh() && (Part->GetFName()==TEXT("EquippedWeapon") || Part->GetFName()==TEXT("EquippedShield")))
            {
                const bool Weapon=Part->GetFName()==TEXT("EquippedWeapon");
                const bool Stored=Visual->AnimationStyle==TEXT("spell");
                const FTransform Expected=(Stored ? (Weapon ? Visual->WeaponStowed : Visual->ShieldStowed) : (Weapon ? Visual->WeaponGrip : Visual->ShieldGrip))
                    *Pawn->GetMesh()->GetSocketTransform(Stored ? TEXT("upper_chest") : Weapon ? TEXT("hand_R") : TEXT("hand_L"));
                TestTrue(*FString::Printf(TEXT("%s %s: equipment follows authored hand/back binding without drift"),*Profiles[Index],*Direction.Key),FVector::Dist(Expected.GetLocation(),Part->GetComponentLocation())<.1f);
            }
            Capture.Frame(Pawn,TEXT("moving_attack_")+Direction.Key);
        }
        // Follow complete actions through direction changes, re-entry, jump and
        // recovery. Single contact poses cannot reveal phase resets or grip drift.
        Pawn->SetActorLocation(FVector(0,0,99)); Pawn->GetCharacterMovement()->StopMovementImmediately();
        const float AttackDuration=Pawn->GetAbilityAnimationDuration(TEXT("attack_melee"));
        const int32 CycleFrames=FMath::CeilToInt(FMath::Max(4.f,AttackDuration+2.f)*60);
        bool bSawAirborne=false, bSawRecovery=false;
        for (int32 Frame=0;Frame<CycleFrames;++Frame)
        {
            if (Frame==0 || Frame==60) Pawn->MulticastPlayAbilityMotion(TEXT("attack_melee"),AttackDuration,false);
            if (Frame==90) Pawn->Jump();
            if (Frame==91) Pawn->StopJumping();
            const FVector Direction=Frame<60 ? FVector(1,0,0) : Frame<120 ? FVector(0,1,0) : FVector(-1,0,0);
            Pawn->AddMovementInput(Direction,1); Advance();
            bSawAirborne|=Pawn->GetCharacterMovement()->IsFalling();
            bSawRecovery|=Frame>60 && !Pawn->IsActionPlaying();
            for (const FTransform& Bone:Pawn->GetMesh()->GetComponentSpaceTransforms()) TestFalse(TEXT("Finite pose throughout combat cycle"),Bone.ContainsNaN());
            TInlineComponentArray<UStaticMeshComponent*> Parts(Pawn);
            for (const auto* Part:Parts) if (Part->GetStaticMesh() && (Part->GetFName()==TEXT("EquippedWeapon") || Part->GetFName()==TEXT("EquippedShield")))
            {
                const bool Weapon=Part->GetFName()==TEXT("EquippedWeapon"), Stored=Visual->AnimationStyle==TEXT("spell");
                const FTransform Expected=(Stored ? (Weapon ? Visual->WeaponStowed : Visual->ShieldStowed) : (Weapon ? Visual->WeaponGrip : Visual->ShieldGrip))
                    *Pawn->GetMesh()->GetSocketTransform(Stored ? TEXT("upper_chest") : Weapon ? TEXT("hand_R") : TEXT("hand_L"));
                TestTrue(TEXT("Equipment binding remains aligned through turns, jump and recovery"),FVector::Dist(Expected.GetLocation(),Part->GetComponentLocation())<.1f);
            }
            if (Frame%5==0 && FParse::Param(FCommandLine::Get(),TEXT("WarCaptureCombatCycle")))
                Capture.Frame(Pawn,FString::Printf(TEXT("cycle_%04d"),Frame/5));
        }
        TestTrue(TEXT("Jump remains possible during a moving attack"),bSawAirborne);
        TestTrue(TEXT("Completed combat returns to locomotion"),bSawRecovery);
        TestTrue(TEXT("Movement continues after animation recovery"),Pawn->GetVelocity().Size2D()>100);
        Pawn->Destroy(); Controller->Destroy(); State->Destroy(); Advance();
    }
    Capture.Save(!HasAnyErrors());
    World->EndPlay(EEndPlayReason::Quit); Instance->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); Instance->RemoveFromRoot();
    return !HasAnyErrors();
}
#endif
