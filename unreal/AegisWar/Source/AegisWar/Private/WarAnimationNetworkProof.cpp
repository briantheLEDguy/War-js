#include "WarAnimationNetworkProof.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarAnimationInstance.h"
#include "WarPlayerState.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityRuntime.h"
#include "WarAttributeSet.h"
#include "WarCombatStatus.h"
#include "WarWrathRelic.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UWarAnimationNetworkProof::ShouldCreateSubsystem(UObject* Outer) const
{
    return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(),TEXT("WarAnimationNetworkProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking"));
}
bool UWarAnimationNetworkProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarAnimationNetworkProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarAnimationNetworkProof,STATGROUP_Tickables); }
void UWarAnimationNetworkProof::Finish(bool bPassed,const FString& Detail)
{
    bFinished=true;
    FString Run,Role; FParse::Value(FCommandLine::Get(),TEXT("WarProofRun="),Run);
    FParse::Value(FCommandLine::Get(),TEXT("WarAnimationProofRole="),Role);
    if (Run.IsEmpty() || Run.Contains(TEXT("..")) || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\"))
        || !TArray<FString>{TEXT("server"),TEXT("client"),TEXT("late-client")}.Contains(Role)) return;
    auto Report=MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"),bPassed);
    Report->SetStringField(TEXT("detail"),Detail); Report->SetStringField(TEXT("role"),Role);
    Report->SetNumberField(TEXT("uniqueVariants"),Seen.Num()); Report->SetBoolField(TEXT("joinedDuringAction"),bJoinedDuringAction);
    Report->SetArrayField(TEXT("samples"),Samples); Report->SetBoolField(TEXT("graphicalAcceptance"),false);
    const FString Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("AnimationNetworkProof"),Run);
    IFileManager::Get().MakeDirectory(*Directory,true); FString Text;
    FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
    FFileHelper::SaveStringToFile(Text,*FPaths::Combine(Directory,Role+TEXT(".json")));
}
void UWarAnimationNetworkProof::Tick(float Delta)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds(); if (Started<0) Started=Now;
    if (Now-Started>240) { Finish(false,TEXT("Timed out collecting all replicated ability variants")); return; }
    const bool bServer=GetWorld()->GetNetMode()==NM_DedicatedServer;
    if (bServer && Actors.IsEmpty())
    {
        // A collision fixture above the existing proof map keeps its content intact.
        auto* Floor=GetWorld()->SpawnActor<AActor>(); auto* Shape=NewObject<UBoxComponent>(Floor);
        Floor->SetRootComponent(Shape); Shape->SetBoxExtent(FVector(3000,3000,20));
        Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Shape->SetCollisionResponseToAllChannels(ECR_Block);
        Floor->SetReplicates(true); Floor->bAlwaysRelevant=true; Shape->SetIsReplicated(true);
        Shape->RegisterComponent(); Floor->SetActorLocation(FVector(0,0,2980));
        const TArray<FString> Profiles={TEXT("civic_battle_prelate_m"),TEXT("civic_sunfire_templar_m"),TEXT("mire_warbrute_m"),TEXT("civic_ember_arcanist_m")};
        for (int32 Index=0;Index<4;++Index) for (bool bTarget:{false,true})
        {
            const FString Profile=bTarget ? (Index==2 ? Profiles[1] : Profiles[2]) : Profiles[Index];
            auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*(TEXT("/Game/MigrationProof/Visual_")+Profile));
            if (!Visual) { Finish(false,TEXT("Missing visual")); return; }
            FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Pawn=GetWorld()->SpawnActor<AWarCharacter>(FVector(bTarget?200:0,Index*600,3099),FRotator::ZeroRotator,Params);
            auto* Controller=GetWorld()->SpawnActor<AAIController>(); Controller->Possess(Pawn);
            auto* State=GetWorld()->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
            State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital"));
            FString Error; if (!Pawn->SetVisualDefinition(Visual,Error)) { Finish(false,Error); return; }
            State->InitializeForPawn(Pawn); State->SetSiegeNormalized(true); State->GetClassAbilities()->InitializeCharacter(Pawn);
            Pawn->bAlwaysRelevant=true; Pawn->GetCharacterMovement()->bUseControllerDesiredRotation=false;
            if (!bTarget) Pawn->Tags.Add(TEXT("SuppliedAnimationNetworkActor"));
            (bTarget?Targets:Actors).Add(Pawn);
        }
        Indices.Init(0,4); Next.Init(Now+10,4); return;
    }
    if (bServer)
    {
        bool bEmitted=false;
        auto* Catalog=GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
        for (int32 Index=0;Index<Actors.Num();++Index)
        {
            auto* Pawn=Actors[Index].Get(); auto* Target=Targets[Index].Get(); if (!Pawn || !Target) { Finish(false,TEXT("Lost proof actor")); return; }
            if (Now<Next[Index]) continue;
            const auto Kit=Catalog->Kit(Pawn->GetCareerId()); const auto* Ability=Kit[Indices[Index]%Kit.Num()];
            auto* State=Pawn->GetPlayerState<AWarPlayerState>(); auto* Runtime=State->GetClassAbilities();
            Runtime->Interrupt(); Runtime->ResetCooldowns(); Runtime->RestoreResource();
            UWarCombatStatus::On(Pawn)->Clear(); UWarCombatStatus::On(Target)->Clear(); AWarWrathRelic::RemoveFor(Pawn);
            Pawn->SetActorLocation(FVector(0,Index*600,3099)); Pawn->SetActorRotation(FRotator::ZeroRotator);
            Pawn->GetCharacterMovement()->StopMovementImmediately(); Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            Target->SetActorLocation(FVector(200,Index*600,3099));
            if (Ability->Id==TEXT("ember_arcanist.flashstep")) Target->SetActorLocation(FVector(0,Index*600+400,3099));
            State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),1000);
            State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),1000);
            Target->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),2000);
            FString Error; if (!Runtime->TryActivate(Ability->Id,Ability->bEnemyTarget?Target:Pawn,Error)) { Finish(false,Ability->Id.ToString()+TEXT(": ")+Error); return; }
            const auto& Motion=Pawn->GetReplicatedMotion(); const FString Key=Pawn->GetAnimationProfile().ToString()+TEXT(":")+Motion.Role.ToString(); Seen.Add(Key);
            if (Samples.IsEmpty()) UE_LOG(LogTemp,Display,TEXT("WAR_SUPPLIED_ANIMATION_STARTED"));
            auto Row=MakeShared<FJsonObject>(); Row->SetStringField(TEXT("key"),Key); Row->SetNumberField(TEXT("serial"),Motion.Serial);
            Row->SetNumberField(TEXT("start"),Motion.Start); Row->SetNumberField(TEXT("duration"),Motion.Duration); Samples.Add(MakeShared<FJsonValueObject>(Row));
            bEmitted=true;
            Next[Index]=Now+Motion.Duration+1; ++Indices[Index];
        }
        // Keep emitting cycles after the receipt so the delayed client sees all variants.
        if (Seen.Num()==41 && bEmitted)
        { Finish(true,TEXT("All authoritative variants emitted")); bFinished=false; bServerReported=true; }
        return;
    }
    if (GetWorld()->GetNetMode()!=NM_Client || !GetWorld()->GetGameState()) return;
    for (TActorIterator<AWarCharacter> It(GetWorld());It;++It)
    {
        auto* Pawn=*It; if (!Pawn->IsVisualReady()) continue;
        Pawn->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        const auto& Motion=Pawn->GetReplicatedMotion(); const double Age=GetWorld()->GetGameState()->GetServerWorldTimeSeconds()-Motion.Start;
        if (!Motion.Role.ToString().Contains(TEXT("__")) || Age<.15 || Age>Motion.Duration-.15) continue;
        auto* Animation=Cast<UWarAnimationInstance>(Pawn->GetMesh()->GetAnimInstance());
        const FName ExpectedState(*(Motion.Role.ToString()+FString::Printf(TEXT(":%d"),Motion.Serial)));
        if (!Animation || Animation->EvaluatedState!=ExpectedState) continue;
        const double EvaluatedAge=Animation->EvaluatedServerTime-Motion.Start;
        const double PoseLag=Age-EvaluatedAge;
        if (PoseLag<-.001 || PoseLag>Delta+.05 || FMath::Abs(Animation->EvaluatedTime-EvaluatedAge)>.12)
        {
            Finish(false,FString::Printf(TEXT("Client pose phase mismatch: %s age=%.6f sampledAge=%.6f evaluated=%.6f selected=%.6f tick=%.6f"),
                *Motion.Role.ToString(),Age,EvaluatedAge,Animation->EvaluatedTime,Animation->CurrentTime,Delta)); return;
        }
        const FString Key=Pawn->GetAnimationProfile().ToString()+TEXT(":")+Motion.Role.ToString();
        if (!InitialProfiles.Contains(Pawn->GetAnimationProfile()))
        { bJoinedDuringAction|=Age>.5; InitialProfiles.Add(Pawn->GetAnimationProfile()); }
        if (Seen.Contains(Key)) continue; Seen.Add(Key);
        auto Row=MakeShared<FJsonObject>(); Row->SetStringField(TEXT("key"),Key); Row->SetNumberField(TEXT("serial"),Motion.Serial);
        Row->SetNumberField(TEXT("start"),Motion.Start); Row->SetNumberField(TEXT("duration"),Motion.Duration);
        Row->SetNumberField(TEXT("age"),EvaluatedAge); Row->SetNumberField(TEXT("evaluatedTime"),Animation->EvaluatedTime);
        Row->SetNumberField(TEXT("poseLag"),PoseLag); Row->SetNumberField(TEXT("frameDelta"),Delta); Samples.Add(MakeShared<FJsonValueObject>(Row));
    }
    if (Seen.Num()==41) Finish(true,TEXT("All variants evaluated using replicated identities and server start times"));
}
