#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeRules.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeEquipment.h"
#include "WarCitadelSiegeProof.h"
#include "WarScenarioInstance.h"
#include "WarCityDefinition.h"
#include "Engine/GameInstance.h"
#include "Components/BoxComponent.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarAbilityRuntime.h"
#include "WarCharacter.h"
#include "WarCombatStatus.h"
#include "WarQuestRules.h"
#include "WarZoneAnchor.h"
#include "GameplayEffect.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Misc/ScopeExit.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    FWarSiegeState Courtyard()
    {
        FWarSiegeState State; WarSiege::Start(State,18,EWarSiegeScenario::FullSiege,2);
        State.Stage=1; State.MainClaims=0x0f; return State;
    }
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelReceiptHashTest,"AegisWar.Foundation.CitadelReceiptSha256",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelPhysicalSnapshotTest,"AegisWar.Foundation.CitadelPhysicalSnapshot",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelPhysicalSnapshotTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Proof=NewObject<UWarCitadelSiegeProof>(World);
    TestFalse(TEXT("A missing encounter has no available diagnostic"),Proof->PhysicalSnapshot()->GetBoolField(TEXT("available")));
    auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();auto* Foreign=World->SpawnActor<AWarSiegeEncounter>();
    Encounter->Battlefield=World->SpawnActor<AWarSiegeBattlefield>();Proof->Encounter=Encounter;
    Encounter->LastSampledPresence.Attackers=6;Encounter->LastSampledPresence.Defenders=0;
    Encounter->LastPresenceSampleAt=World->GetTimeSeconds();
    auto* Cart=World->SpawnActor<AWarSiegeEquipment>();Cart->SetOwner(Encounter);Cart->Travel=123;Cart->bMoving=true;Cart->Engineers.SetNum(2);
    auto* OtherCart=World->SpawnActor<AWarSiegeEquipment>();OtherCart->SetOwner(Foreign);
    Encounter->Convoy={Cart,OtherCart};
    const auto Before=Encounter->Siege;const auto Position=Cart->GetActorLocation();
    const auto Snapshot=Proof->PhysicalSnapshot();
    TestTrue(TEXT("An owned field supplies diagnostic data"),Snapshot->GetBoolField(TEXT("available")));
    TestTrue(TEXT("Diagnostic has no acceptance semantics"),Snapshot->GetBoolField(TEXT("diagnosticOnly")));
    TestEqual(TEXT("Actual sampled presence is retained"),Snapshot->GetNumberField(TEXT("qualifyingAttackers")),6.);
    TestEqual(TEXT("Actual array count exposes foreign entries"),Snapshot->GetNumberField(TEXT("convoyCount")),2.);
    const auto& Vehicles=Snapshot->GetArrayField(TEXT("vehicles"));
    if (!TestEqual(TEXT("Foreign-owned vehicles are excluded"),Vehicles.Num(),1)) return false;
    const auto Vehicle=Vehicles[0]->AsObject();
    TestEqual(TEXT("Actual travel is reported"),Vehicle->GetNumberField(TEXT("travelCm")),123.);
    TestTrue(TEXT("Movement intent is observed without stopping"),Vehicle->GetBoolField(TEXT("moving")) && Cart->bMoving);
    TestEqual(TEXT("Missing crew seats remain explicit"),Vehicle->GetArrayField(TEXT("engineers")).Num(),2);
    TestTrue(TEXT("Read-only sample preserves cart position"),Cart->GetActorLocation().Equals(Position,0));
    TestTrue(TEXT("Read-only sample preserves claims and elapsed time"),Encounter->Siege.MainClaims==Before.MainClaims && Encounter->Siege.Elapsed==Before.Elapsed);
    return true;
}
bool FWarCitadelReceiptHashTest::RunTest(const FString& Parameters)
{
    FString Hash, Error;
    const FString EmptyExpected=TEXT("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    const FString BinaryExpected=TEXT("362a6af8803ec30f59a7097f5041054246b49da8592f8e85a9221824189f354e");
    TestTrue(TEXT("The actual engine provider computes empty bytes"),WarCitadelProofHash::Bytes(nullptr,0,Hash,Error));
    TestEqual(TEXT("Empty bytes match the standard SHA-256 vector"),Hash,EmptyExpected);
    TestTrue(TEXT("The actual engine provider computes abc UTF-8"),WarCitadelProofHash::Text(TEXT("abc"),Hash,Error));
    TestEqual(TEXT("abc matches the standard SHA-256 vector"),Hash,FString(TEXT("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")));
    TestTrue(TEXT("Non-ASCII text uses exact UTF-8 bytes"),WarCitadelProofHash::Text(TEXT("Aegis \u00e9 \U0001f6e1"),Hash,Error));
    TestEqual(TEXT("UTF-8 matches an independently computed vector"),Hash,FString(TEXT("7b11059c8073f5195eda482e238ab36ac37fb5113095f7ba9d281615918be209")));
    TArray<uint8> Binary={0,255,1,128,0,10,13,0,42};
    TestTrue(TEXT("Binary input retains embedded zero and nontext bytes"),WarCitadelProofHash::Bytes(Binary.GetData(),Binary.Num(),Hash,Error));
    TestEqual(TEXT("Binary input matches its independent SHA-256 vector"),Hash,BinaryExpected);
    const FString Directory=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/CitadelReceiptHash"));
    if (!TestTrue(TEXT("Temporary hash fixture directory exists"),IFileManager::Get().MakeDirectory(*Directory,true))) return false;
    const FString Filename=Directory/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".bin")),EmptyFilename=Filename+TEXT(".empty");
    ON_SCOPE_EXIT { IFileManager::Get().Delete(*Filename); IFileManager::Get().Delete(*EmptyFilename); };
    if (!TestTrue(TEXT("Temporary binary file was written"),FFileHelper::SaveArrayToFile(Binary,*Filename))) return false;
    TestTrue(TEXT("Real file hashing reads the same bytes as the provider vector"),WarCitadelProofHash::File(Filename,Hash,Error));
    TestEqual(TEXT("File padding and encoding do not alter a binary receipt"),Hash,BinaryExpected);
    const TArray<uint8> Empty;
    if (!TestTrue(TEXT("Temporary empty file was written"),FFileHelper::SaveArrayToFile(Empty,*EmptyFilename))) return false;
    TestTrue(TEXT("A real empty file is a valid SHA-256 input"),WarCitadelProofHash::File(EmptyFilename,Hash,Error));
    TestEqual(TEXT("Empty file matches the standard SHA-256 vector"),Hash,EmptyExpected);
    Binary.Add(1);if (!TestTrue(TEXT("Actual changed file was written"),FFileHelper::SaveArrayToFile(Binary,*Filename))) return false;
    TestTrue(TEXT("Changed file remains readable"),WarCitadelProofHash::File(Filename,Hash,Error));
    TestNotEqual(TEXT("A changed byte invalidates the previous exact receipt"),Hash,BinaryExpected);
    TestFalse(TEXT("Missing file fails recoverably"),WarCitadelProofHash::File(Filename+TEXT(".missing"),Hash,Error));
    TestTrue(TEXT("Missing file clears stale receipt bytes"),Hash.IsEmpty());TestFalse(TEXT("Missing file explains recovery failure"),Error.IsEmpty());
    TestFalse(TEXT("Null nonempty input fails before touching memory"),WarCitadelProofHash::Bytes(nullptr,1,Hash,Error));
    TestFalse(TEXT("Negative input length fails recoverably"),WarCitadelProofHash::Bytes(Binary.GetData(),-1,Hash,Error));
    TestFalse(TEXT("Oversized input fails before reading or allocating"),WarCitadelProofHash::Bytes(Binary.GetData(),int64(MAX_int32)+1,Hash,Error));
    TestTrue(TEXT("Rejected input never leaves a usable stale hash"),Hash.IsEmpty());
    TestTrue(TEXT("Recovery after rejected input still uses the real provider"),WarCitadelProofHash::Text(TEXT(""),Hash,Error));
    TestEqual(TEXT("Empty text and bytes have identical SHA-256"),Hash,EmptyExpected);
    TestTrue(TEXT("Successful hashing clears the prior recovery error"),Error.IsEmpty());
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelRecoveryWalWitnessTest,"AegisWar.Foundation.CitadelRecoveryWalWitness",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelRecoveryWalWitnessTest::RunTest(const FString& Parameters)
{
    auto* World=UWorld::CreateWorld(EWorldType::Game,false);if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Player=World->SpawnActor<AWarPlayerController>();Player->ScenarioCharacterId=TEXT("stable-wal-character");
    auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();Encounter->ActivationId=TEXT("actual-owner-activation");
    auto* Proof=NewObject<UWarCitadelSiegeProof>(World);Proof->Encounter=Encounter;Proof->RecoveryHost=TEXT("private-wal-witness");
    Proof->RecoveryWalDirectory=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/CitadelRecoveryWal")/FGuid::NewGuid().ToString(EGuidFormats::Digits));
    if (!IFileManager::Get().MakeDirectory(*Proof->RecoveryWalDirectory,true)) return false;
    const FString File=Proof->RecoveryWalDirectory/TEXT("original.json"),Duplicate=Proof->RecoveryWalDirectory/TEXT("duplicate.json");
    ON_SCOPE_EXIT { IFileManager::Get().Delete(*File);IFileManager::Get().Delete(*Duplicate);IFileManager::Get().DeleteDirectory(*Proof->RecoveryWalDirectory); };
    auto Runtime=MakeShared<FJsonObject>();Runtime->SetNumberField(TEXT("version"),2);Runtime->SetNumberField(TEXT("capturedAtUnixMs"),123456789);
    Runtime->SetStringField(TEXT("testOpaquePayload"),TEXT("Exact é native bytes"));
    auto Document=MakeShared<FJsonObject>();Document->SetObjectField(TEXT("runtime"),Runtime);
    auto Character=MakeShared<FJsonObject>();Character->SetStringField(TEXT("id"),Player->ScenarioCharacterId);Character->SetObjectField(TEXT("document"),Document);
    auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("hostId"),Proof->RecoveryHost);Body->SetStringField(TEXT("characterId"),Player->ScenarioCharacterId);
    Body->SetStringField(TEXT("activationId"),Encounter->ActivationId);Body->SetStringField(TEXT("requestId"),TEXT("original-request"));
    Body->SetNumberField(TEXT("baseRevision"),7);Body->SetNumberField(TEXT("walSequence"),3);Body->SetObjectField(TEXT("character"),Character);
    auto Record=MakeShared<FJsonObject>();Record->SetNumberField(TEXT("schemaVersion"),1);Record->SetStringField(TEXT("hostId"),Proof->RecoveryHost);Record->SetObjectField(TEXT("body"),Body);
    const auto Write=[&](const FString& Filename) { FString Text;FJsonSerializer::Serialize(Record,TJsonWriterFactory<>::Create(&Text));
        return FFileHelper::SaveStringToFile(Text,*Filename,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM); };
    if (!Write(File)) return false;FString OriginalHash,AfterHash,Error;WarCitadelProofHash::File(File,OriginalHash,Error);
    TSharedPtr<FJsonObject> Witness;const auto Actual=Proof->RecoveryWalCharacter(Player,Witness,Error);
    if (!TestNotNull(TEXT("Actual flushed bytes supply the mutation witness"),Actual.Get())) { AddError(Error);return false; }
    TestTrue(TEXT("WAL character retains exact encoded fields without recapturing UTC"),FJsonValue::CompareEqual(FJsonValueObject(Actual),FJsonValueObject(Character)));
    TestEqual(TEXT("Receipt hashes the original byte buffer"),Witness->GetStringField(TEXT("sha256")),OriginalHash);
    TestEqual(TEXT("Original request identity survives"),Witness->GetStringField(TEXT("requestId")),FString(TEXT("original-request")));
    WarCitadelProofHash::File(File,AfterHash,Error);TestEqual(TEXT("Reading evidence never rewrites its original WAL"),AfterHash,OriginalHash);
    if (!Write(Duplicate)) return false;
    TestNull(TEXT("Two records cannot ambiguously witness one successful mutation"),Proof->RecoveryWalCharacter(Player,Witness,Error).Get());IFileManager::Get().Delete(*Duplicate);
    Body->SetStringField(TEXT("activationId"),TEXT("foreign-activation"));Write(File);
    TestNull(TEXT("Foreign activation cannot witness the owning character mutation"),Proof->RecoveryWalCharacter(Player,Witness,Error).Get());
    Body->SetStringField(TEXT("activationId"),Encounter->ActivationId);Body->SetStringField(TEXT("walSequence"),TEXT("3"));Write(File);
    TestNull(TEXT("Coerced CAS values do not witness a trusted WAL"),Proof->RecoveryWalCharacter(Player,Witness,Error).Get());
    FFileHelper::SaveStringToFile(TEXT("{broken"),*File);
    TestNull(TEXT("Damaged WAL evidence fails recoverably"),Proof->RecoveryWalCharacter(Player,Witness,Error).Get());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelProgressTest,"AegisWar.Foundation.CitadelParallelObjectives",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelProgressTest::RunTest(const FString& Parameters)
{
    for (bool RightFirst : {false,true})
    {
        auto State=Courtyard(); FWarSiegePresence Presence; Presence.Attackers=18; Presence.bCrewAlive=false;
        WarSiege::Tick(State,Presence,40);
        TestEqual(TEXT("Locked plaza occupants cannot capture"),State.Progress,0.f);
        (RightFirst ? Presence.RightAttackers : Presence.LeftAttackers)=1;
        WarSiege::Tick(State,Presence,91);
        TestEqual(TEXT("Either first side is an explicit permanent claim"),State.MainClaims,uint8(RightFirst ? 0x2f : 0x1f));
        TestFalse(TEXT("One side cannot unlock plaza"),WarSiege::CenterUnlocked(State));
        Presence={}; WarSiege::Tick(State,Presence,30);
        TestEqual(TEXT("Captured side cannot decay"),RightFirst ? State.RightProgress : State.LeftProgress,1.f);
        (RightFirst ? Presence.LeftAttackers : Presence.RightAttackers)=1;
        Presence.Attackers=18; Presence.bCrewAlive=false; WarSiege::Tick(State,Presence,91);
        TestTrue(TEXT("Both sides unlock center"),WarSiege::CenterUnlocked(State));
        TestEqual(TEXT("Unlocking sample never captures locked center"),State.Progress,0.f);
        TestFalse(TEXT("Plaza requires players without engineers"),WarSiege::RequiresCrew(State));
        WarSiege::Tick(State,Presence,40);
        TestEqual(TEXT("Pure player plaza opens keep transition"),State.Phase,EWarSiegePhase::Transition);
        TestEqual(TEXT("All courtyard claims are explicit"),State.MainClaims,uint8(0x7f));
        WarSiege::Tick(State,{},60); Presence={}; Presence.bCommanderDead=true; WarSiege::Tick(State,Presence,.1);
        TestTrue(TEXT("Commander wins only after keep stage"),State.bAttackersWon);
        TestEqual(TEXT("Eight required claims maintained"),State.MainClaims,uint8(0xff));
        TestTrue(TEXT("Completed encounter resets"),WarSiege::Start(State,18));
        TestEqual(TEXT("Reset clears both independent sides"),State.MainClaims,uint8(0));
    }
    auto State=Courtyard(); FWarSiegePresence Presence; Presence.LeftAttackers=1; Presence.RightAttackers=1;
    WarSiege::Tick(State,Presence,20);
    TestTrue(TEXT("Both sides progress concurrently"),State.LeftProgress>0 && State.RightProgress>0);
    const float Left=State.LeftProgress,Right=State.RightProgress;
    Presence.LeftDefenders=1; WarSiege::Tick(State,Presence,10);
    TestEqual(TEXT("Left contest freezes only left"),State.LeftProgress,Left);
    TestTrue(TEXT("Uncontested right continues"),State.RightProgress>Right);
    Presence={}; WarSiege::Tick(State,Presence,12);
    TestTrue(TEXT("Unfinished sides decay independently after grace"),State.LeftProgress<Left && State.RightProgress>State.LeftProgress);
    State=Courtyard(); Presence={}; Presence.LeftAttackers=6; Presence.RightAttackers=6; Presence.OptionalAttackers=6;
    WarSiege::Tick(State,Presence,45);
    TestEqual(TEXT("Simultaneous side claims neither overwrite the other"),State.MainClaims,uint8(0x3f));
    TestEqual(TEXT("Optional stage defense is independent"),State.OptionalClaims,uint8(2));
    TestEqual(TEXT("Optional success never claims center"),State.Progress,0.f);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelCheckpointTest,"AegisWar.Foundation.CitadelCheckpointRecovery",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelCheckpointTest::RunTest(const FString& Parameters)
{
    auto State=Courtyard(); State.MainClaims=0x1f; State.LeftProgress=1; State.RightProgress=.43f;
    State.RightAbsence=7; State.OptionalProgress=.32f; State.OptionalAbsence=3; State.Elapsed=432.5;
    State.Remaining=590; State.ContestedSeconds=12; State.MilestoneSeconds={90,180,270,360,420};
    auto Json=UWarCampaignSiegeSubsystem::Snapshot(State,false); FWarSiegeState Restored; FString Error;
    TestTrue(TEXT("Durable independent partial state restores"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    TestEqual(TEXT("Restore retains right progress"),Restored.RightProgress,State.RightProgress);
    TestEqual(TEXT("Restore retains right absence"),Restored.RightAbsence,7.);
    TestEqual(TEXT("Restore retains permanent claims"),Restored.MainClaims,uint8(0x1f));
    TestEqual(TEXT("Restore retains remaining stage"),Restored.Remaining,590.);
    TestEqual(TEXT("Restore retains recorded rules"),Restored.RulesVersion,2);
    TestEqual(TEXT("Restore retains milestone receipts"),Restored.MilestoneSeconds.Num(),5);
    State.Elapsed=3000.5; Json=UWarCampaignSiegeSubsystem::Snapshot(State,false);
    TestTrue(TEXT("Bounded capture substep elapsed tolerance"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    Json->SetNumberField(TEXT("elapsed"),3001.1);
    TestFalse(TEXT("Elapsed beyond tolerance fails"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    Json->SetNumberField(TEXT("elapsed"),500); Json->SetNumberField(TEXT("remaining"),841);
    TestFalse(TEXT("Actual stage clock remains strict"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    State=Courtyard(); State.MainClaims=0x4f; Json=UWarCampaignSiegeSubsystem::Snapshot(State,false);
    TestFalse(TEXT("Center claim without both sides rejected"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    State.Stage=2; State.MainClaims=0x7f; State.Phase=EWarSiegePhase::Finished; State.bAttackersWon=true; State.Remaining=0;
    Json=UWarCampaignSiegeSubsystem::Snapshot(State,false);
    TestFalse(TEXT("Recovery cannot invent commander victory"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    State.MainClaims=0xff; Json=UWarCampaignSiegeSubsystem::Snapshot(State,false);
    TestTrue(TEXT("Recorded complete commander result restores"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    State=Courtyard(); State.bOvertime=true; State.Remaining=72;
    Json=UWarCampaignSiegeSubsystem::Snapshot(State,false);
    TestTrue(TEXT("Bounded overtime restores"),UWarCampaignSiegeSubsystem::RestoreSnapshot(Json,Restored,Error));
    TestTrue(TEXT("Overtime state retained"),Restored.bOvertime); TestEqual(TEXT("Overtime remainder retained"),Restored.Remaining,72.);
    FWarSiegeState Unknown; TestFalse(TEXT("Unknown recorded rules cannot be reinterpreted"),WarSiege::Start(Unknown,18,EWarSiegeScenario::FullSiege,3));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelScopeTest,"AegisWar.Foundation.CitadelEncounterScope",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelScopeTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false; GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Campaign=World->SpawnActor<AWarSiegeEncounter>(); Campaign->bCampaign=true; Campaign->ActivationId=TEXT("scope"); Campaign->Siege=Courtyard();
    auto* Scenario=World->SpawnActor<AWarSiegeEncounter>(); Scenario->Siege=Courtyard();
    auto* CampaignState=World->SpawnActor<AWarPlayerState>(); CampaignState->SetDevelopmentRealm(EWarRealm::Aegis); CampaignState->SetSiegeMembership(Campaign);
    auto* ScenarioState=World->SpawnActor<AWarPlayerState>(); ScenarioState->SetSiegeMembership(Scenario); ScenarioState->SetSiegeNormalized(true);
    auto* OtherState=World->SpawnActor<AWarPlayerState>(); OtherState->SetDevelopmentRealm(EWarRealm::Riftbound); OtherState->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
    auto* Pawn=World->SpawnActor<AWarCharacter>(); Pawn->SetPlayerState(CampaignState); CampaignState->GetAbilitySystemComponent()->InitAbilityActorInfo(CampaignState,Pawn);
    const auto Before=CampaignState->GetInventory();
    auto* ScenarioPawn=World->SpawnActor<AWarCharacter>(); ScenarioPawn->SetPlayerState(ScenarioState);
    auto* OutsidePawn=World->SpawnActor<AWarCharacter>(); OutsidePawn->SetPlayerState(OtherState);
    CampaignState->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
    TestTrue(TEXT("Remote pending seat retains ordinary combat scope"),AWarSiegeEncounter::SharesCombatScope(Pawn,OutsidePawn));
    TestFalse(TEXT("An unrelated scenario never joins that scope"),AWarSiegeEncounter::SharesCombatScope(Pawn,ScenarioPawn));
    TestFalse(TEXT("Remote pending membership does not force siege healing rules"),CampaignState->UsesSiegeTargeting());
    auto* ASC=CampaignState->GetAbilitySystemComponent();
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),100); ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxManaAttribute(),100);
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),73); ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),61);
    auto Runtime=CampaignState->CaptureScenarioState(); auto Cooldown=MakeShared<FJsonObject>(); Cooldown->SetStringField(TEXT("id"),TEXT("ordinary.cooldown")); Cooldown->SetNumberField(TEXT("remaining"),19);
    Runtime->GetObjectField(TEXT("abilities"))->SetArrayField(TEXT("cooldowns"),{MakeShared<FJsonValueObject>(Cooldown)}); CampaignState->RestoreScenarioState(Runtime);
    auto* Effect=NewObject<UGameplayEffect>(); Effect->DurationPolicy=EGameplayEffectDurationType::Infinite;
    const auto Handle=ASC->ApplyGameplayEffectToSelf(Effect,1,ASC->MakeEffectContext());
    TestFalse(TEXT("Campaign membership never normalizes stats"),CampaignState->IsSiegeNormalized());
    TestEqual(TEXT("Owner-specific lookup ignores another encounter"),AWarSiegeEncounter::For(Pawn),Campaign);
    TestEqual(TEXT("Fixture has ordinary health before cleanup"),CampaignState->GetAttributes()->GetHealth(),73.f);
    TestEqual(TEXT("Fixture has ordinary mana before cleanup"),CampaignState->GetAttributes()->GetMana(),61.f);
    Campaign->Siege.MainClaims=0x1f; Campaign->Siege.LeftProgress=1; Campaign->Siege.RightProgress=.43f;
    Campaign->Siege.Elapsed=123.5; Campaign->Siege.Remaining=712;
    AddExpectedError(TEXT("WAR_CAMPAIGN_SIEGE_BLOCKED"),EAutomationExpectedErrorFlags::Contains,1);
    Campaign->FailMatch(TEXT("Content fixture spawn is obstructed.")); Campaign->Tick(2);
    TestTrue(TEXT("Live content failure blocks execution independently of transport"),Campaign->bContentBlocked && Campaign->bLeasePaused);
    TestEqual(TEXT("Live failure preserves the recorded phase"),int32(Campaign->Siege.Phase),int32(EWarSiegePhase::Active));
    TestEqual(TEXT("Live failure preserves permanent claims"),Campaign->Siege.MainClaims,uint8(0x1f));
    TestEqual(TEXT("Live failure preserves unfinished side progress"),Campaign->Siege.RightProgress,.43f);
    TestEqual(TEXT("Live failure preserves elapsed time"),Campaign->Siege.Elapsed,123.5);
    TestEqual(TEXT("Live failure holds the stage clock"),Campaign->Siege.Remaining,712.);
    TestEqual(TEXT("Live failure retains its activation identity"),Campaign->ActivationId,FString(TEXT("scope")));
    TestTrue(TEXT("Live failure retains human membership"),Campaign->Owns(CampaignState));
    TestTrue(TEXT("Live failure retains the normal avatar"),IsValid(Pawn));
    TestEqual(TEXT("Live failure retains normal health"),CampaignState->GetAttributes()->GetHealth(),73.f);
    TestEqual(TEXT("Live failure retains normal cooldowns"),CampaignState->GetClassAbilities()->Cooldown(TEXT("ordinary.cooldown")),19.f);
    TestTrue(TEXT("Live failure preserves unrelated ASC effects"),ASC->GetActiveGameplayEffect(Handle)!=nullptr);
    TestFalse(TEXT("A remote member remains outside capital protection"),Campaign->IsProtected(Pawn));
    Campaign->ResetRound();
    TestFalse(TEXT("Explicit content repair reset clears the local block"),Campaign->bContentBlocked);
    TestTrue(TEXT("Campaign cleanup preserves the normal avatar"),IsValid(Pawn));
    TestEqual(TEXT("Campaign cleanup preserves health"),CampaignState->GetAttributes()->GetHealth(),73.f);
    TestEqual(TEXT("Campaign cleanup preserves mana"),CampaignState->GetAttributes()->GetMana(),61.f);
    TestEqual(TEXT("Campaign cleanup preserves cooldowns"),CampaignState->GetClassAbilities()->Cooldown(TEXT("ordinary.cooldown")),19.f);
    TestTrue(TEXT("Campaign cleanup preserves unrelated ASC effects"),ASC->GetActiveGameplayEffect(Handle)!=nullptr);
    TestEqual(TEXT("Saved inventory revision unchanged"),CampaignState->GetInventory().Revision,Before.Revision);
    TestTrue(TEXT("Other encounter membership remains"),Scenario->Owns(ScenarioState));
    TestTrue(TEXT("Other scenario normalization remains"),ScenarioState->IsSiegeNormalized());
    TestEqual(TEXT("Other-zone character location remains"),OtherState->GetCurrentZone(),FName(TEXT("dawnline_expanse")));
    TestFalse(TEXT("Cleanup releases only owned membership"),CampaignState->IsSiegeMember());
    Campaign->SafeEvacuationZones.FindOrAdd(EWarRealm::Aegis).Add(TEXT("dawnline_expanse"));
    TestTrue(TEXT("Trusted explicitly secured neighboring zone allowed"),Campaign->CanEvacuate(EWarRealm::Aegis,TEXT("dawnline_expanse")));
    TestFalse(TEXT("Enemy or unspecified destination refused"),Campaign->CanEvacuate(EWarRealm::Aegis,TEXT("rift_gate_fortress")));
    TestFalse(TEXT("Allowlist cannot cross realm"),Campaign->CanEvacuate(EWarRealm::Riftbound,TEXT("dawnline_expanse")));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelGateTest,"AegisWar.Foundation.CitadelClaimGates",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelGateTest::RunTest(const FString& Parameters)
{
    auto* World=UWorld::CreateWorld(EWorldType::Game,false); if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL()); auto* Battlefield=World->SpawnActor<AWarSiegeBattlefield>();
    auto* Outer=World->SpawnActor<AActor>(); auto* Inner=World->SpawnActor<AActor>(); Battlefield->StageGates={Outer,Inner};
    FWarSiegeState State; State.Phase=EWarSiegePhase::Active; State.MainClaims=0x20;
    Battlefield->ApplyMilestones(State); TestTrue(TEXT("A right side claim cannot open lower gate"),Outer->GetActorEnableCollision());
    TestEqual(TEXT("Right ownership never fabricates left"),WarSiege::ClaimedObjectives(State),uint16(0x20));
    State.MainClaims=0x3f; Battlefield->ApplyMilestones(State);
    TestFalse(TEXT("Breach claim opens lower gate"),Outer->GetActorEnableCollision()); TestTrue(TEXT("Both sides alone keep inner gate closed"),Inner->GetActorEnableCollision());
    State.MainClaims=0x7f; Battlefield->ApplyMilestones(State); TestFalse(TEXT("Center claim opens keep"),Inner->GetActorEnableCollision());
    State={}; Battlefield->ApplyMilestones(State); TestTrue(TEXT("Reset restores scenario gate collision"),Outer->GetActorEnableCollision() && Inner->GetActorEnableCollision());
    Battlefield->bLiveCapitalOverlay=true; Battlefield->ApplyMilestones(State);
    TestFalse(TEXT("Idle live overlay preserves ordinary city traversal"),Outer->GetActorEnableCollision() || Inner->GetActorEnableCollision());
    State.Phase=EWarSiegePhase::Active; Battlefield->ApplyMilestones(State);
    TestTrue(TEXT("Activated lower-city stage closes live siege gates"),Outer->GetActorEnableCollision() && Inner->GetActorEnableCollision());
    State={}; Battlefield->ApplyMilestones(State);
    TestFalse(TEXT("Campaign settlement restores ordinary traversal"),Outer->GetActorEnableCollision() || Inner->GetActorEnableCollision());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelBaselineTest,"AegisWar.Foundation.CitadelEarnedBaseline",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelBaselineTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Field=World->SpawnActor<AWarSiegeBattlefield>();auto* Encounter=World->SpawnActor<AWarSiegeEncounter>();Encounter->Battlefield=Field;
    for (int32 I=0;I<2;++I)
    {
        auto* Gate=World->SpawnActor<AActor>();auto* Part=NewObject<UBoxComponent>(Gate);
        Gate->SetRootComponent(Part);Gate->AddInstanceComponent(Part);Part->RegisterComponent();Field->StageGates.Add(Gate);
    }
    auto* Proof=NewObject<UWarCitadelSiegeProof>(World);Proof->bPerformanceBaseline=true;Proof->Encounter=Encounter;
    FString Error;TestTrue(TEXT("Ordinary rules start the benchmark at stage zero"),WarSiege::Start(Encounter->Siege,18,EWarSiegeScenario::FullSiege,2));
    Field->ApplyMilestones(Encounter->Siege);
    TestTrue(TEXT("The baseline records actual zero claims and closed gates"),Proof->ObserveBaselineProgression(Error));
    auto Observation=Proof->BaselineObservations.Last()->AsObject();
    TestEqual(TEXT("The initial clock is the genuine 840-second stage"),Observation->GetNumberField(TEXT("stageRemainingSeconds")),840.);
    TestEqual(TEXT("The baseline witnesses both actual gate assemblies"),Observation->GetArrayField(TEXT("gates")).Num(),2);
    TestEqual(TEXT("Each gate reports its real native primitive"),Observation->GetArrayField(TEXT("gates"))[0]->AsObject()->GetArrayField(TEXT("components")).Num(),1);
    Field->StageGates[0]->SetActorEnableCollision(false);
    TestFalse(TEXT("Forced gate opening without a claim cannot become baseline evidence"),Proof->ObserveBaselineProgression(Error));
    Field->ApplyMilestones(Encounter->Siege);
    const auto Initial=Encounter->Siege;
    Encounter->Siege.Stage=2;Encounter->Siege.MainClaims=127;Encounter->Siege.Elapsed=7;Encounter->Siege.MilestoneSeconds={1,2,3,4,5,6,7};
    TestFalse(TEXT("Direct stage initialization is rejected after the initial witness"),Proof->ObserveBaselineProgression(Error));
    auto* Late=NewObject<UWarCitadelSiegeProof>(World);Late->bPerformanceBaseline=true;Late->Encounter=Encounter;
    TestFalse(TEXT("A fresh baseline cannot start with prefabricated claims"),Late->ObserveBaselineProgression(Error));Encounter->Siege=Initial;
    FWarSiegePresence Presence;Presence.Attackers=1;Presence.OptionalAttackers=1;
    const auto Advance=[&](const TCHAR* Label,const TFunctionRef<bool()>& Done)
    {
        for (int32 Step=0;Step<20000 && !Done();++Step)
        {
            WarSiege::Tick(Encounter->Siege,Presence,.05);Field->ApplyMilestones(Encounter->Siege);
            if (!Proof->ObserveBaselineProgression(Error)) { AddError(Error);return false; }
        }
        return TestTrue(Label,Done());
    };
    if (!Advance(TEXT("Four real lower-city rule captures earn the first transition"),[&] { return Encounter->Siege.Phase==EWarSiegePhase::Transition; })) return false;
    TestEqual(TEXT("Lower captures preserve their actual milestone count"),Encounter->Siege.MilestoneSeconds.Num(),4);
    TestFalse(TEXT("Earned breach opens the outer physical assembly"),Field->StageGates[0]->GetActorEnableCollision());
    TestTrue(TEXT("The keep assembly remains closed before plaza capture"),Field->StageGates[1]->GetActorEnableCollision());
    const auto Transition=Encounter->Siege;
    Encounter->Siege.Stage=1;Encounter->Siege.Phase=EWarSiegePhase::Active;Encounter->Siege.Remaining=840;
    TestFalse(TEXT("Skipping the sixty-second transition is rejected"),Proof->ObserveBaselineProgression(Error));Encounter->Siege=Transition;
    Presence={};if (!Advance(TEXT("The actual transition clock earns stage one"),[&] { return Encounter->Siege.Stage==1; })) return false;
    Presence.LeftAttackers=1;Presence.RightAttackers=1;Presence.Attackers=1;
    if (!Advance(TEXT("Parallel side and pure-player center captures earn the keep"),[&] { return Encounter->Siege.Phase==EWarSiegePhase::Transition; })) return false;
    const auto Earned=Encounter->Siege;Encounter->Siege.MilestoneSeconds[0]+=1;
    TestFalse(TEXT("Previously earned milestone timestamps are immutable"),Proof->ObserveBaselineProgression(Error));Encounter->Siege=Earned;
    Presence={};if (!Advance(TEXT("The second actual sixty-second transition earns stage two"),[&] { return Encounter->Siege.Stage==2; })) return false;
    TestEqual(TEXT("Stage two retains the seven real capture events"),Encounter->Siege.MilestoneSeconds.Num(),7);
    TestEqual(TEXT("The benchmark stops before any commander claim"),Encounter->Siege.MainClaims,uint8(127));
    TestTrue(TEXT("The benchmark records genuine optional ownership independently"),(Encounter->Siege.OptionalClaims&1)!=0);
    TestTrue(TEXT("A final observation contains the actual active stage-two clocks"),Proof->ObserveBaselineProgression(Error,true));
    TestFalse(TEXT("Rule evidence alone does not claim a completed crowd exposure"),Proof->bBaselineSettled);
    TestEqual(TEXT("Both gate assemblies are hidden only after their earned milestones"),Field->StageGates[0]->IsHidden() && Field->StageGates[1]->IsHidden(),true);
    Presence.bCommanderDead=true;WarSiege::Tick(Encounter->Siege,Presence,.05);Field->ApplyMilestones(Encounter->Siege);
    TestFalse(TEXT("A commander outcome is outside this baseline fixture's acceptance"),Proof->ObserveBaselineProgression(Error));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelDefendedCampaignTest,"AegisWar.Foundation.CitadelDefendedCampaign",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelDefendedCampaignTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    auto* Proof=NewObject<UWarCitadelSiegeProof>(World);Proof->bLive=true;Proof->bLiveDefended=true;Proof->Round=1;
    FWarSiegeState State;TestTrue(TEXT("The live defense starts normal full-siege 18v18 rules"),WarSiege::Start(State,18,EWarSiegeScenario::FullSiege,2));
    FWarSiegePresence Contest;Contest.Attackers=18;Contest.Defenders=18;
    WarSiege::Tick(State,Contest,20);
    TestTrue(TEXT("Ordinary opening presence contests without manufacturing ownership"),State.ContestedSeconds>19 && State.MainClaims==0);
    TestFalse(TEXT("An active stage cannot be acknowledged as an already defended fixture"),Proof->ExpectedFinishedOutcome(State));
    WarSiege::Tick(State,{},819.5);
    TestFalse(TEXT("Disengagement does not force an early result"),Proof->ExpectedFinishedOutcome(State));
    WarSiege::Tick(State,{},.5);
    TestTrue(TEXT("Only the genuine stage clock earns the defended outcome"),Proof->ExpectedFinishedOutcome(State));
    TestTrue(TEXT("The observed elapsed time is the ordinary fourteen-minute stage"),FMath::IsNearlyEqual(State.Elapsed,840.,1.e-6));
    TestEqual(TEXT("The genuine defense produces exactly one rule result"),State.ResultCount,1);
    TestEqual(TEXT("No fictional capture events are supplied"),State.MilestoneSeconds.Num(),0);
    TestFalse(TEXT("The normal defense never claims commander victory"),State.bAttackersWon);
    auto Invalid=State;Invalid.MainClaims=1;
    TestFalse(TEXT("A partial attacker capture is outside this zero-claim defense fixture"),Proof->ExpectedFinishedOutcome(Invalid));
    Invalid=State;Invalid.Stage=2;
    TestFalse(TEXT("A late-stage reset cannot masquerade as the initial city defense"),Proof->ExpectedFinishedOutcome(Invalid));
    Invalid=State;Invalid.Elapsed=1;
    TestFalse(TEXT("An invented timeout is rejected"),Proof->ExpectedFinishedOutcome(Invalid));
    Invalid=State;Invalid.bOvertime=true;Invalid.Elapsed=900;
    TestFalse(TEXT("A zero-claim initial objective cannot fabricate final-objective overtime"),Proof->ExpectedFinishedOutcome(Invalid));
    Proof->bLiveDefended=false;
    TestFalse(TEXT("The default live fixture continues to require the attacker outcome"),Proof->ExpectedFinishedOutcome(State));
    Proof->bLive=false;Proof->Round=2;
    TestTrue(TEXT("The existing second scenario defense retains its recorded behavior"),Proof->ExpectedFinishedOutcome(State));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelScenarioCandidateTest,"AegisWar.Foundation.CitadelScenarioCandidate",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelScenarioCandidateTest::RunTest(const FString& Parameters)
{
    TestTrue(TEXT("The isolated native proof accepts an explicit numeric loopback port"),WarScenarioCandidateProof::LoopbackUrl(TEXT("http://127.0.0.1:65535")));
    for (const TCHAR* Url:{TEXT("http://127.0.0.1:0"),TEXT("http://127.0.0.1:65536"),TEXT("http://127.0.0.1:123/x"),
        TEXT("http://127.0.0.1:123@elsewhere"),TEXT("http://localhost:123"),TEXT("http://192.168.0.1:123"),TEXT("http://127.0.0.1:-1")})
        TestFalse(TEXT("Private candidate queue connections reject alternate hosts, credentials and invalid ports"),WarScenarioCandidateProof::LoopbackUrl(Url));
    const auto Descriptor=[]()
    {
        auto Row=MakeShared<FJsonObject>();const FString Signature=FString::ChrN(64,'a'),Revision=FString::ChrN(64,'c');
        const FString Map=TEXT("/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/SiegeCandidate");
        Row->SetNumberField(TEXT("schemaVersion"),1);Row->SetStringField(TEXT("fixtureId"),TEXT("12345678-1234-4123-8123-123456789abc"));
        Row->SetStringField(TEXT("map"),Map);Row->SetStringField(TEXT("signature"),Signature);Row->SetStringField(TEXT("geometrySignature"),FString::ChrN(64,'b'));
        Row->SetStringField(TEXT("cityRevision"),Revision);Row->SetStringField(TEXT("mapSha256"),FString::ChrN(64,'d'));
        Row->SetStringField(TEXT("cityDefinition"),TEXT("/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/City"));
        Row->SetStringField(TEXT("scenario"),TEXT("lower_city"));Row->SetStringField(TEXT("battlefield"),TEXT("FullSiege"));Row->SetStringField(TEXT("statsMode"),TEXT("scenario"));
        Row->SetNumberField(TEXT("capacity"),18);Row->SetNumberField(TEXT("rulesVersion"),2);
        Row->SetBoolField(TEXT("proofOnly"),true);Row->SetBoolField(TEXT("contentReviewOverride"),true);
        for (const TCHAR* Key:{TEXT("productionAdmission"),TEXT("steamAdmission"),TEXT("territorialAcceptance"),TEXT("releaseApproved")}) Row->SetBoolField(Key,false);
        auto Definition=MakeShared<FJsonObject>();Definition->SetStringField(TEXT("id"),TEXT("lower_city"));Definition->SetStringField(TEXT("name"),TEXT("Siege of Bastion of Aegis"));
        Definition->SetStringField(TEXT("description"),TEXT("Breach the city, capture both side objectives and the courtyard, then defeat the commander."));
        Definition->SetStringField(TEXT("map"),Map);Definition->SetStringField(TEXT("contentRevision"),Revision);
        Definition->SetStringField(TEXT("battlefield"),TEXT("FullSiege"));Definition->SetNumberField(TEXT("rulesVersion"),2);Definition->SetNumberField(TEXT("capacity"),18);
        Definition->SetNumberField(TEXT("gatherMs"),30000);Definition->SetNumberField(TEXT("acceptMs"),30000);Definition->SetNumberField(TEXT("reconnectMs"),120000);
        Row->SetObjectField(TEXT("definition"),Definition);return Row;
    };
    FString Error;TestTrue(TEXT("The private descriptor retains the original full scenario contract"),WarScenarioCandidateProof::Identity(Descriptor(),Error));
    for (const TCHAR* Key:{TEXT("productionAdmission"),TEXT("steamAdmission"),TEXT("territorialAcceptance"),TEXT("releaseApproved")})
    { auto Row=Descriptor();Row->SetBoolField(Key,true);TestFalse(TEXT("Private queue evidence cannot mint admission or territorial approval"),WarScenarioCandidateProof::Identity(Row,Error)); }
    auto Row=Descriptor();Row->SetNumberField(TEXT("capacity"),19);TestFalse(TEXT("Private entry cannot exceed normal realm capacity"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->GetObjectField(TEXT("definition"))->SetNumberField(TEXT("gatherMs"),0);TestFalse(TEXT("Private entry cannot skip gathering"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->GetObjectField(TEXT("definition"))->SetNumberField(TEXT("reconnectMs"),0);TestFalse(TEXT("Private entry preserves bounded reconnect reservations"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->GetObjectField(TEXT("definition"))->SetNumberField(TEXT("rulesVersion"),1);TestFalse(TEXT("Historical rules cannot be silently reinterpreted"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->SetStringField(TEXT("fixtureId"),TEXT("12345678-1234-1123-8123-123456789abc"));TestFalse(TEXT("An isolated version-four fixture identity is required"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->SetStringField(TEXT("map"),TEXT("/Game/Capitals/Siege/AegisCapital_Siege"));TestFalse(TEXT("Private review never alters canonical GM admission"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->SetStringField(TEXT("map"),TEXT("/Game/WorldRebuild/AegisCitadel_AAAAAAAAAAAA/SiegeCandidate"));TestFalse(TEXT("Private candidate namespace must match the exact signed revision"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->SetStringField(TEXT("cityDefinition"),TEXT("/Game/WorldRebuild/AegisCitadel_AAAAAAAAAAAA/City"));TestFalse(TEXT("The private city namespace must retain exact signed case"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->GetObjectField(TEXT("definition"))->SetStringField(TEXT("map"),TEXT("/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/siegecandidate"));TestFalse(TEXT("The immutable scenario map cannot alias another spelling"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->SetStringField(TEXT("map"),TEXT("/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaab/SiegeCandidate"));TestFalse(TEXT("A different lower-case namespace cannot claim the signed candidate"),WarScenarioCandidateProof::Identity(Row,Error));
    Row=Descriptor();Row->SetStringField(TEXT("capacity"),TEXT("18"));TestFalse(TEXT("Typed receipt fields cannot be coerced"),WarScenarioCandidateProof::Identity(Row,Error));
    TestFalse(TEXT("A descriptor flag alone cannot bypass actual file and package receipts"),WarScenarioCandidateProof::Bindings(Descriptor(),Error));
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World);World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());auto* Field=World->SpawnActor<AWarSiegeBattlefield>();Field->DefinitionVersion=2;
    Field->CityDefinition=NewObject<UWarCityDefinition>();Field->CityDefinition->Revision=FString::ChrN(64,'c');
    TestFalse(TEXT("Actual foreign map or city ownership blocks the transient review"),WarScenarioCandidateProof::Battlefield(Descriptor(),Field,Error));
    TestFalse(TEXT("Rejected descriptors never mark the authored traversal reviewed"),Field->bTraversalReviewed);
    TestFalse(TEXT("Rejected descriptors never mark the authored roster reviewed"),Field->bEquippedRosterReviewed);
    auto* Instance=NewObject<UWarScenarioInstance>(NewObject<UGameInstance>(World));
    TestTrue(TEXT("Ordinary scenario validation retains its unchanged path"),Instance->ReviewCandidate(Field,Error));
    TestFalse(TEXT("The ordinary path never fabricates a review flag"),Field->bTraversalReviewed || Field->bEquippedRosterReviewed);
    return !HasAnyErrors();
}
#endif
