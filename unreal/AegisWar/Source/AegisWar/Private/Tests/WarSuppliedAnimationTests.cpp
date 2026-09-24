#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarAnimationInstance.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarGameMode.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityRuntime.h"
#include "WarAttributeSet.h"
#include "WarCombatStatus.h"
#include "WarWrathRelic.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/WorldSettings.h"
#include "WarAnimationGameplayCapture.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSuppliedAnimationTest,"AegisWar.Foundation.SuppliedAnimationGameplay",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarSuppliedAnimationTest::RunTest(const FString& Parameters)
{
    auto* Instance=NewObject<UGameInstance>(GEngine); Instance->AddToRoot(); Instance->InitializeStandalone();
    UWorld* World=Instance->GetWorld();
    World->InitializeActorsForPlay(FURL()); World->BeginPlay(); World->GetWorldSettings()->NotifyBeginPlay();
    FWarAnimationGameplayCapture Capture(World);
    auto* Catalog=Instance->GetSubsystem<UWarAbilityCatalog>();
    const auto Box=[&](FVector Center,FVector Extent)
    {
        auto* Actor=World->SpawnActor<AActor>(); auto* Shape=NewObject<UBoxComponent>(Actor);
        Actor->SetRootComponent(Shape); Shape->SetBoxExtent(Extent); Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Shape->SetCollisionObjectType(ECC_WorldStatic); Shape->SetCollisionResponseToAllChannels(ECR_Block);
        Shape->RegisterComponent(); Actor->SetActorLocation(Center); return Actor;
    };
    Box(FVector(0,0,-20),FVector(5000,5000,20));
    const auto Advance=[&](float Seconds)
    { for (int32 Frame=0;Frame<FMath::CeilToInt(Seconds*60);++Frame) { ++GFrameCounter; World->Tick(LEVELTICK_All,1.f/60); } };
    const auto Health=[](AWarCharacter* Pawn) { return Pawn->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth(); };
    const auto Spawn=[&](const FString& Profile,FVector Position,bool bBot)
    {
        auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*(TEXT("/Game/MigrationProof/Visual_")+Profile));
        if (!TestNotNull(*Profile,Visual)) return static_cast<AWarCharacter*>(nullptr);
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Pawn=World->SpawnActor<AWarCharacter>(Position,FRotator::ZeroRotator,Params);
        AController* Controller=bBot ? static_cast<AController*>(World->SpawnActor<AAIController>()) : World->SpawnActor<APlayerController>();
        // A server-side remote PlayerController waits for client movement RPCs.
        // Give the player fixture a local owner so Jump follows the input path.
        if (!bBot) CastChecked<APlayerController>(Controller)->SetPlayer(NewObject<ULocalPlayer>(GEngine));
        Controller->Possess(Pawn); auto* State=World->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
        State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
        FString Error; TestTrue(*FString::Printf(TEXT("%s visual: %s"),*Profile,*Error),Pawn->SetVisualDefinition(Visual,Error));
        State->InitializeForPawn(Pawn); State->SetSiegeNormalized(true); State->GetClassAbilities()->InitializeCharacter(Pawn);
        Pawn->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Pawn->GetCharacterMovement()->bUseControllerDesiredRotation=false;
        TestTrue(TEXT("Spawned gameplay actor has begun play"),Pawn->HasActorBegunPlay());
        TestTrue(TEXT("Spawned gameplay actor ticks"),Pawn->IsActorTickEnabled());
        return Pawn;
    };
    TArray<TSharedPtr<FJsonValue>> Evidence;
    const auto Record=[&](AWarCharacter* Pawn,FName Role,const FString& Kind)
    {
        auto Row=MakeShared<FJsonObject>(); Row->SetStringField(TEXT("profile"),Pawn->GetAnimationProfile().ToString());
        Row->SetStringField(TEXT("role"),Role.ToString()); Row->SetStringField(TEXT("scenario"),Kind);
        Row->SetNumberField(TEXT("time"),World->GetTimeSeconds()); Row->SetNumberField(TEXT("motionSerial"),Pawn->GetReplicatedMotion().Serial);
        Evidence.Add(MakeShared<FJsonValueObject>(Row));
        if (Capture.Enabled() && !Kind.EndsWith(TEXT("_ability"))) Capture.Frame(Pawn,Kind+TEXT("_")+Role.ToString());
    };
    const TArray<FString> Profiles={TEXT("civic_battle_prelate_m"),TEXT("civic_sunfire_templar_m"),TEXT("mire_warbrute_m"),TEXT("civic_ember_arcanist_m")};
    int32 Executed=0;
    for (const FString& Profile:Profiles) for (bool bBot:{false,true})
    {
        auto* Pawn=Spawn(Profile,FVector(0,0,99),bBot); if (!Pawn) continue;
        auto* Target=Spawn(Profile==TEXT("mire_warbrute_m") ? TEXT("civic_sunfire_templar_m") : TEXT("mire_warbrute_m"),FVector(200,0,99),true);
        if (!Target) continue;
        auto* State=Pawn->GetPlayerState<AWarPlayerState>(); auto* Runtime=State->GetClassAbilities();
        const auto Kit=Catalog->Kit(Pawn->GetCareerId()); TestEqual(TEXT("Ten reachable abilities"),Kit.Num(),10);
        Advance(.2f); TestNotNull(TEXT("Native animation instance is active"),Cast<UWarAnimationInstance>(Pawn->GetMesh()->GetAnimInstance()));
        const FString Executor=bBot ? TEXT("participant_bot") : TEXT("player");
        for (const auto* Ability:Kit)
        {
            const auto* Recipe=Pawn->GetAbilityPresentation(Ability->Id);
            if (!TestNotNull(*Ability->Id.ToString(),Recipe)) continue;
            TSet<FName> Variants;
            for (int32 Variant=0;Variant<Recipe->VariantRoles.Num();++Variant)
            {
                Runtime->Interrupt(); Runtime->ResetCooldowns(); Runtime->RestoreResource();
                AWarWrathRelic::RemoveFor(Pawn); UWarCombatStatus::On(Pawn)->Clear(); UWarCombatStatus::On(Target)->Clear();
                Pawn->GetCharacterMovement()->StopMovementImmediately(); Pawn->SetActorLocation(FVector(0,0,99)); Pawn->SetActorRotation(FRotator::ZeroRotator);
                Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking); Target->SetActorLocation(FVector(200,0,99));
                if (Ability->Id==TEXT("ember_arcanist.flashstep")) Target->SetActorLocation(FVector(0,400,99));
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),1000);
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),1000);
                Target->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),2000);
                Advance(.1f);
                FString Error; AActor* Aim=Ability->bEnemyTarget ? Target : Pawn;
                if (!TestTrue(*(Ability->Id.ToString()+TEXT(" ")+Executor+TEXT(": ")+Error),Runtime->TryActivate(Ability->Id,Aim,Error)))
                { AddError(Error); continue; }
                const auto Motion=Pawn->GetReplicatedMotion(); Variants.Add(Motion.Role);
                TestTrue(TEXT("Server selects an authored variant"),Recipe->VariantRoles.Contains(Motion.Role));
                TestEqual(TEXT("Replicated duration is authoritative"),Motion.Duration,Recipe->Duration);
                const float Before=Health(Target); const float OwnBefore=Health(Pawn);
                const FVector Hand=Pawn->GetMesh()->GetBoneLocation(TEXT("hand_R")); float HandTravel=0;
                const float CapsuleStart=Pawn->GetActorLocation().Z; float CapsuleRise=0;
                float MaximumPosePhaseError=0; int32 EvaluatedFrames=0;
                const auto* EquippedVisual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*(TEXT("/Game/MigrationProof/Visual_")+Profile));
                TInlineComponentArray<UStaticMeshComponent*> Equipped(Pawn); float GripLag=0;
                TArray<float> CaptureTimes={.3f,Recipe->ContactSeconds-.05f,Recipe->ContactSeconds+.05f,Recipe->Duration-.2f};
                CaptureTimes.Sort(); int32 Captured=0;
                while (World->GetTimeSeconds()<Motion.Start+Recipe->Duration+.85)
                {
                    Advance(1.f/60);
                    const auto* EvaluatedAnimation=CastChecked<UWarAnimationInstance>(Pawn->GetMesh()->GetAnimInstance());
                    if (EvaluatedAnimation->EvaluatedState==FName(*(Motion.Role.ToString()+FString::Printf(TEXT(":%d"),Motion.Serial))))
                    {
                        ++EvaluatedFrames;
                        MaximumPosePhaseError=FMath::Max(MaximumPosePhaseError,static_cast<float>(FMath::Abs(
                            EvaluatedAnimation->EvaluatedTime-(EvaluatedAnimation->EvaluatedServerTime-Motion.Start))));
                    }
                    CapsuleRise=FMath::Max(CapsuleRise,static_cast<float>(Pawn->GetActorLocation().Z-CapsuleStart));
                    HandTravel=FMath::Max(HandTravel,static_cast<float>(FVector::Dist(Hand,Pawn->GetMesh()->GetBoneLocation(TEXT("hand_R")))));
                    if (EquippedVisual->AnimationStyle!=TEXT("spell"))
                        for (const auto* Part:Equipped) if (Part->GetStaticMesh()
                            && (Part->GetFName()==TEXT("EquippedWeapon") || Part->GetFName()==TEXT("EquippedShield")))
                        {
                            const bool bWeapon=Part->GetFName()==TEXT("EquippedWeapon");
                            const auto* Animation=CastChecked<UWarAnimationInstance>(Pawn->GetMesh()->GetAnimInstance());
                            const FName ExpectedState(*(Motion.Role.ToString()+FString::Printf(TEXT(":%d"),Motion.Serial)));
                            const float Age=Animation->EvaluatedState==ExpectedState ? Animation->EvaluatedTime
                                : static_cast<float>(World->GetTimeSeconds()-Motion.Start);
                            const float Stow=Recipe->bStowEquipment ? FMath::Clamp(FMath::Min(Age/.3f,(Motion.Duration-Age)/.3f),0.f,1.f) : 0;
                            const bool bStored=Pawn->IsActionPlaying() && Stow>=1-KINDA_SMALL_NUMBER;
                            const FTransform Relative=bStored ? (bWeapon ? EquippedVisual->WeaponStowed : EquippedVisual->ShieldStowed)
                                : (bWeapon ? EquippedVisual->WeaponGrip : EquippedVisual->ShieldGrip);
                            const FTransform Expected=Relative*Pawn->GetMesh()->GetSocketTransform(bStored ? TEXT("upper_chest")
                                : bWeapon ? TEXT("hand_R") : TEXT("hand_L"));
                            const float ErrorCm=FVector::Dist(Expected.GetLocation(),Part->GetComponentLocation());
                            if (GripLag<.1f && ErrorCm>=.1f)
                                UE_LOG(LogTemp,Display,TEXT("WAR_GRIP_DRIFT %s %s t=%.3f actual=%s expected=%s"),*Ability->Id.ToString(),*Part->GetName(),World->GetTimeSeconds()-Motion.Start,*Part->GetComponentLocation().ToString(),*Expected.GetLocation().ToString());
                            GripLag=FMath::Max(GripLag,ErrorCm);
                        }
                    if (Capture.Enabled() && !bBot && Captured<CaptureTimes.Num() && World->GetTimeSeconds()>=Motion.Start+CaptureTimes[Captured])
                        Capture.Frame(Pawn,Motion.Role.ToString()+FString::Printf(TEXT("_phase%d"),Captured++));
                    if (World->GetTimeSeconds()<Motion.Start+Recipe->ContactSeconds-.035)
                    { TestEqual(TEXT("No hostile effect before authored contact"),Health(Target),Before); TestEqual(TEXT("No heal before authored contact"),Health(Pawn),OwnBefore); }
                }
                TestFalse(TEXT("Action completes its recovery"),Runtime->IsBusy());
                TestTrue(*(Ability->Id.ToString()+TEXT(" animates the equipped skeleton")),HandTravel>.1f);
                TestTrue(*(Ability->Id.ToString()+TEXT(" publishes completed pose evaluation")),EvaluatedFrames>0);
                TestTrue(*FString::Printf(TEXT("%s evaluated pose follows sampled server time: %.5f seconds"),*Ability->Id.ToString(),MaximumPosePhaseError),MaximumPosePhaseError<.04f);
                TestTrue(*FString::Printf(TEXT("%s equipment follows finalized bones: maximum drift %.4f cm"),*Ability->Id.ToString(),GripLag),GripLag<.1f);
                if (Recipe->Movement==TEXT("leap"))
                {
                    TestTrue(TEXT("Airborne action moves the authoritative capsule"),CapsuleRise>10);
                    TestTrue(TEXT("Airborne action returns the capsule to its floor"),FMath::Abs(Pawn->GetActorLocation().Z-CapsuleStart)<3);
                }
                if (Ability->Effects.ContainsByPredicate([](const auto& E){return E.Kind==TEXT("damage");}))
                    TestTrue(*(Ability->Id.ToString()+TEXT(" delivers hostile damage")),Health(Target)<Before);
                Record(Pawn,Motion.Role,Executor+TEXT("_ability")); ++Executed;
            }
            TestEqual(TEXT("Every cosmetic variant is selected"),Variants.Num(),Recipe->VariantRoles.Num());
        }
        Runtime->Interrupt(); UWarCombatStatus::On(Pawn)->Clear(); AWarWrathRelic::RemoveFor(Pawn);
        Target->SetActorLocation(FVector(2000,2000,99));
        // Drive the actual direction selection while using the same movement
        // component velocity consumed during ordinary player and bot movement.
        const TArray<TPair<FName,FVector>> Moves={{TEXT("walk"),FVector(180,0,0)},{TEXT("run"),FVector(500,0,0)},
            {TEXT("walk_backward"),FVector(-150,0,0)},{TEXT("strafe_left"),FVector(0,-150,0)},{TEXT("strafe_right"),FVector(0,150,0)}};
        Pawn->SetActorRotation(FRotator::ZeroRotator);
        for (const auto& Move:Moves)
        {
            for (int32 Frame=0;Frame<18;++Frame)
            { Pawn->GetCharacterMovement()->Velocity=Move.Value; Advance(1.f/60); }
            TestEqual(TEXT("Directional locomotion selects the matching state"),Pawn->GetPlayingAnimation(),Move.Key);
            Record(Pawn,Move.Key,Executor+TEXT("_locomotion"));
        }
        Pawn->GetCharacterMovement()->StopMovementImmediately(); Advance(1);
        Record(Pawn,Pawn->GetPlayingAnimation(),Executor+TEXT("_idle"));
        for (const auto& Turn:TArray<TPair<FName,float>>{{TEXT("turn_left"),-90},{TEXT("turn_right"),90}})
        {
            Pawn->AddActorWorldRotation(FRotator(0,Turn.Value,0)); Advance(1.f/60);
            TestEqual(TEXT("Turn in place state"),Pawn->GetPlayingAnimation(),Turn.Key);
            Advance(.25f); Record(Pawn,Turn.Key,Executor+TEXT("_turn")); Advance(4);
        }
        Pawn->SetActorLocation(FVector(0,0,99)); Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking); Advance(.2f);
        TestTrue(*(Profile+TEXT(" ")+Executor+TEXT(" grounded character can jump")),Pawn->CanJump());
        Pawn->Jump(); Advance(.1f); TestEqual(*(Profile+TEXT(" ")+Executor+TEXT(" actual jump uses supplied jump")),Pawn->GetPlayingAnimation(),FName(TEXT("jump"))); Record(Pawn,TEXT("jump"),Executor+TEXT("_jump"));
        bool Landed=false;
        for (int32 Frame=0;Frame<120;++Frame) { Advance(1.f/60); if (Pawn->GetPlayingAnimation()==TEXT("landing")) Landed=true; }
        TestTrue(TEXT("Landing recovery is reached"),Landed); if (Landed) Record(Pawn,TEXT("landing"),Executor+TEXT("_landing"));
        Pawn->SetActorRotation(FRotator::ZeroRotator);
        for (const auto& Hit:TArray<TPair<FName,float>>{{TEXT("hit_front"),200},{TEXT("hit_back"),-200}})
        {
            Target->SetActorLocation(FVector(Hit.Value,0,99)); Pawn->ReactToHit(Target,100); Advance(.05f);
            TestEqual(TEXT("Hit direction selects supplied reaction"),Pawn->GetPlayingAnimation(),Hit.Key); Record(Pawn,Hit.Key,Executor+TEXT("_reaction")); Advance(4);
        }
        Pawn->HandleDeath(); Advance(.1f); TestEqual(TEXT("Death state is reached"),Pawn->GetPlayingAnimation(),FName(TEXT("death"))); Record(Pawn,TEXT("death"),Executor+TEXT("_death"));
        Advance(3);
        TInlineComponentArray<UStaticMeshComponent*> EquipmentParts(Pawn);
        for (auto* Equipment:EquipmentParts)
        {
            if (Equipment->GetStaticMesh() && (Equipment->GetFName()==TEXT("EquippedWeapon") || Equipment->GetFName()==TEXT("EquippedShield")))
                TestTrue(TEXT("Released equipment rests above the floor"),Equipment->Bounds.GetBox().Min.Z>=-.1f);
        }
        Pawn->GetController()->Destroy(); Target->GetController()->Destroy(); Pawn->Destroy(); Target->Destroy(); Advance(.1f);
    }
    TestEqual(TEXT("Forty abilities plus the second Smash variant execute for player and bot"),Executed,82);
    // Exercise the production respawn callback with the retained player choice.
    {
        auto* Mode=World->SpawnActor<AWarGameMode>();
        auto* Start=World->SpawnActor<APlayerStart>(FVector(0,0,99),FRotator::ZeroRotator);
        for (const FString& Profile:Profiles)
        {
            auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*(TEXT("/Game/MigrationProof/Visual_")+Profile));
            auto* Controller=World->SpawnActor<AWarPlayerController>();
            Controller->SetPlayer(NewObject<ULocalPlayer>(GEngine));
            auto* State=World->SpawnActor<AWarPlayerState>(); Controller->SetPlayerState(State);
            State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
            Controller->BeginCharacterEntry(Visual); Mode->RestartPlayerAtPlayerStart(Controller,Start); Advance(.3f);
            auto* Original=Cast<AWarCharacter>(Controller->GetPawn());
            if (TestNotNull(TEXT("Selected character enters through GameMode"),Original))
            {
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),0);
                Original->HandleDeath(); Mode->RespawnAfterDeath(Original); Advance(6);
                auto* Reborn=Cast<AWarCharacter>(Controller->GetPawn());
                if (TestNotNull(TEXT("Death timer respawns the selected character"),Reborn))
                {
                    TestTrue(TEXT("Respawn creates a fresh pawn"),Reborn!=Original);
                    TestEqual(TEXT("Respawn keeps the selected profile"),Reborn->GetAnimationProfile(),FName(*Profile));
                    TestFalse(TEXT("Respawn clears death state"),Reborn->IsDead());
                    TestTrue(TEXT("Respawn restores health"),State->GetAttributes()->GetHealth()>0);
                    Advance(.2f); TestEqual(TEXT("Respawn resumes supplied idle"),Reborn->GetPlayingAnimation(),FName(TEXT("idle")));
                    Record(Reborn,TEXT("idle"),TEXT("player_respawn")); Reborn->Destroy();
                }
            }
            Controller->Destroy(); State->Destroy(); Advance(.1f);
        }
        Start->Destroy(); Mode->Destroy();
    }
    // Exercise collision after activation as well as preflight. A moving obstacle
    // must cancel the contact event instead of letting the capsule cross it.
    {
        auto* Pawn=Spawn(TEXT("civic_battle_prelate_m"),FVector(0,0,99),false);
        auto* Target=Spawn(TEXT("mire_warbrute_m"),FVector(700,0,99),true);
        auto* State=Pawn->GetPlayerState<AWarPlayerState>(); auto* Runtime=State->GetClassAbilities();
        const auto Reset=[&]()
        {
            Runtime->Interrupt(); Runtime->ResetCooldowns(); Runtime->RestoreResource();
            UWarCombatStatus::On(Pawn)->Clear(); UWarCombatStatus::On(Target)->Clear();
            Pawn->GetCharacterMovement()->StopMovementImmediately(); Pawn->SetActorLocation(FVector(0,0,99));
            Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking); Pawn->SetActorRotation(FRotator::ZeroRotator);
            State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),1000);
            State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),1000);
            Target->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),2000);
            Advance(.2f);
        };
        FString Error; Reset();
        auto* Wall=Box(FVector(350,0,35),FVector(20,100,35));
        const float Mana=State->GetAttributes()->GetMana();
        TestFalse(TEXT("Penance rejects a capsule obstruction below the aiming ray"),Runtime->TryActivate(TEXT("battle_prelate.penance_step"),Target,Error));
        TestEqual(TEXT("Rejected travel spends no mana"),State->GetAttributes()->GetMana(),Mana);
        TestEqual(TEXT("Rejected travel starts no cooldown"),Runtime->Cooldown(TEXT("battle_prelate.penance_step")),0.f);
        Wall->Destroy(); Advance(.1f); Reset();
        auto* Roof=Box(FVector(0,0,220),FVector(120,120,20));
        TestFalse(TEXT("Smash rejects insufficient overhead clearance"),Runtime->TryActivate(TEXT("battle_prelate.reliquary_smash"),Pawn,Error));
        TestEqual(TEXT("Rejected leap spends no mana"),State->GetAttributes()->GetMana(),Mana);
        Roof->Destroy(); Advance(.1f); Reset();
        const float Before=Health(Target);
        TestTrue(TEXT("Penance starts on an unobstructed path"),Runtime->TryActivate(TEXT("battle_prelate.penance_step"),Target,Error));
        Wall=Box(FVector(350,0,35),FVector(20,100,35)); Advance(6);
        TestFalse(TEXT("A new obstacle cancels the moving action"),Runtime->IsBusy());
        TestTrue(TEXT("Capsule never crosses the obstacle"),Pawn->GetActorLocation().X<330);
        TestEqual(TEXT("Collision cancels the pending damage event"),Health(Target),Before);
        Record(Pawn,TEXT("penance_step"),TEXT("dynamic_obstacle_cancellation"));
        Wall->Destroy(); Advance(.1f); Reset(); Target->SetActorLocation(FVector(200,0,99));
        TestTrue(TEXT("Litany starts before interruption"),Runtime->TryActivate(TEXT("battle_prelate.litany_of_strikes"),Target,Error));
        Advance(.05f); Runtime->Interrupt(); Advance(6);
        TestEqual(TEXT("Interrupted contact never applies damage"),Health(Target),Before);
        TestFalse(TEXT("Interrupted action clears busy state"),Runtime->IsBusy());
        TestTrue(TEXT("Interrupted motion stays at its capsule position"),FVector::Dist2D(Pawn->GetActorLocation(),FVector::ZeroVector)<1);
        Record(Pawn,TEXT("litany_strike"),TEXT("interrupted_before_contact"));
        Pawn->GetController()->Destroy(); Target->GetController()->Destroy(); Pawn->Destroy(); Target->Destroy(); Advance(.1f);
    }
    auto Report=MakeShared<FJsonObject>(); Report->SetArrayField(TEXT("scenarios"),Evidence);
    Report->SetNumberField(TEXT("abilityExecutions"),Executed); Report->SetBoolField(TEXT("passed"),!HasAnyErrors());
    Report->SetBoolField(TEXT("graphicalAcceptance"),false); Report->SetBoolField(TEXT("networkVerified"),false);
    FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("supplied-animation-gameplay.json")));
    Capture.Save(!HasAnyErrors());
    World->EndPlay(EEndPlayReason::Quit); Instance->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); Instance->RemoveFromRoot();
    return !HasAnyErrors();
}
#endif
