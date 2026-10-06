#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarCampaignMutation.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeBattlefield.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarAttributeSet.h"
#include "WarScenarioTransport.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Misc/ScopeExit.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "GameFramework/CharacterMovementComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelMutationTest,"AegisWar.Foundation.CitadelDurableCharacterMutation",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelMutationTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* Bridge=World->GetSubsystem<UWarCampaignSiegeSubsystem>(); if (!Bridge) return false;
    Bridge->Url=TEXT("http://127.0.0.1"); Bridge->Token=TEXT("test-only-unused-token"); Bridge->HostId=TEXT("native-mutation-test");
    auto* State=World->SpawnActor<AWarPlayerState>(); State->SetDevelopmentRealm(EWarRealm::Aegis);
    auto* Player=World->SpawnActor<AWarPlayerController>(); Player->PlayerState=State; State->SetOwner(Player);
    Player->ScenarioCharacterId=TEXT("stable-native-mutation"); Player->bCampaignIdentityProvisioned=true;
    auto* Siege=World->SpawnActor<AWarSiegeEncounter>(); Siege->bCampaign=true; Siege->ActivationId=TEXT("recorded-test-activation"); State->SetSiegeMembership(Siege);
    auto* ASC=State->GetAbilitySystemComponent(); ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),100);
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxManaAttribute(),100); ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),73);
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),61);
    const auto Before=State->GetInventory(); const FGuid Reward=FGuid::NewGuid(); FString Error;
    Bridge->bBusy=true;
    TestFalse(TEXT("In-flight host checkpoint rejects a successful mutation before acknowledgment"),State->GrantCharacterRewards(Reward,25,5,{},Error));
    TestEqual(TEXT("Rejected WAL commit rolls back inventory revision"),State->GetInventory().Revision,Before.Revision);
    TestEqual(TEXT("Rejected WAL commit rolls back earned gold"),State->GetInventory().CharacterProgression.Gold,Before.CharacterProgression.Gold);
    TestEqual(TEXT("Rejected WAL commit rolls back earned XP"),State->GetInventory().CharacterProgression.Xp,Before.CharacterProgression.Xp);
    TestEqual(TEXT("Rejected WAL commit rolls back the reward receipt"),State->CaptureScenarioState()->GetArrayField(TEXT("rewards")).Num(),0);
    TestEqual(TEXT("Rejected WAL commit preserves health"),State->GetAttributes()->GetHealth(),73.f);
    TestEqual(TEXT("Rejected WAL commit preserves mana"),State->GetAttributes()->GetMana(),61.f);
    {
        FWarCampaignMutation Outer(State);
        TestTrue(TEXT("Nested mutation joins the outer document instead of issuing a partial WAL"),State->GrantCharacterRewards(Reward,25,5,{},Error));
        TestEqual(TEXT("Inner mutation completes before the outer barrier"),State->GetInventory().Revision,Before.Revision+1);
        TestFalse(TEXT("Outer barrier rejects the whole operation while checkpoint is in flight"),Outer.Commit(Error));
    }
    TestEqual(TEXT("Nested rollback restores the complete outer document"),State->GetInventory().Revision,Before.Revision);
    TestEqual(TEXT("Nested rollback also restores receipts"),State->CaptureScenarioState()->GetArrayField(TEXT("rewards")).Num(),0);
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),0);
    TestFalse(TEXT("Defeated failed commit remains rejected"),State->GrantCharacterRewards(Reward,25,5,{},Error));
    TestEqual(TEXT("Rollback never revives a defeated document"),State->GetAttributes()->GetHealth(),0.f);
    State->SetSiegeMembership(nullptr);
    TestTrue(TEXT("Unrelated ordinary transactions retain their existing behavior"),State->GrantCharacterRewards(Reward,25,5,{},Error));
    auto Ack=MakeShared<FJsonObject>(); Ack->SetStringField(TEXT("characterId"),Player->ScenarioCharacterId);
    Ack->SetNumberField(TEXT("revision"),7); Ack->SetNumberField(TEXT("walSequence"),3); Ack->SetBoolField(TEXT("recoveryPending"),false);
    Bridge->ObserveAcks(Ack);
    TestEqual(TEXT("Host acknowledgment captures current CAS revision"),Bridge->CharacterAcks[Player->ScenarioCharacterId].Revision,7);
    TestEqual(TEXT("Host acknowledgment captures WAL sequence"),Bridge->CharacterAcks[Player->ScenarioCharacterId].WalSequence,3);
    Ack->SetNumberField(TEXT("revision"),6); Ack->SetNumberField(TEXT("walSequence"),2); Bridge->ObserveAcks(Ack);
    TestEqual(TEXT("Stale acknowledgment cannot rewind CAS base"),Bridge->CharacterAcks[Player->ScenarioCharacterId].Revision,7);
    const FString Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/CitadelMutation"));
    IFileManager::Get().MakeDirectory(*Folder,true); const FString Filename=Folder/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));
    ON_SCOPE_EXIT { IFileManager::Get().Delete(*Filename); };
    auto Record=MakeShared<FJsonObject>(); Record->SetNumberField(TEXT("schemaVersion"),1); Record->SetStringField(TEXT("characterId"),Player->ScenarioCharacterId);
    TestTrue(TEXT("Native WAL write flushes its complete document"),UWarCampaignSiegeSubsystem::FlushMutationWal(Filename,Record,Error));
    auto Read=WarScenarioTransport::ReadConfig(Filename);
    TestTrue(TEXT("Flushed native record can be read after the write handle closes"),Read && Read->GetStringField(TEXT("characterId"))==Player->ScenarioCharacterId);
    TestFalse(TEXT("Unacknowledged WAL record cannot be overwritten"),UWarCampaignSiegeSubsystem::FlushMutationWal(Filename,Record,Error));
    TestFalse(TEXT("Unavailable WAL destination reports failure instead of success"),UWarCampaignSiegeSubsystem::FlushMutationWal(Folder/TEXT("missing")/TEXT("record.json"),Record,Error));
    auto* Avatar=World->SpawnActor<AWarCharacter>(); Avatar->SetPlayerState(State); Player->Possess(Avatar);
    Avatar->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    State->SetScenarioTransferPending(true);
    TestEqual(TEXT("A durability hold stops ordinary walking"),uint8(Avatar->GetCharacterMovement()->MovementMode),uint8(MOVE_None));
    State->SetScenarioTransferPending(false);
    TestEqual(TEXT("An acknowledgment restores the prior movement mode"),uint8(Avatar->GetCharacterMovement()->MovementMode),uint8(MOVE_Walking));
    State->SetScenarioTransferPending(true);
    Player->UnPossess();
    auto* Replacement=World->SpawnActor<AWarCharacter>(); Replacement->SetPlayerState(State);
    Replacement->GetCharacterMovement()->SetMovementMode(MOVE_Walking); Player->Possess(Replacement);
    TestTrue(TEXT("Replacement admission retains the pending durable return"),State->IsScenarioTransferPending());
    TestEqual(TEXT("Authoritative possession holds a replacement pawn before visual readiness"),uint8(Replacement->GetCharacterMovement()->MovementMode),uint8(MOVE_None));
    State->SetScenarioTransferPending(false);
    TestEqual(TEXT("Final acknowledgment restores replacement movement"),uint8(Replacement->GetCharacterMovement()->MovementMode),uint8(MOVE_Walking));
    Bridge->Encounter=Siege; Siege->bPreparing=true;
    Siege->Battlefield=World->SpawnActor<AWarSiegeBattlefield>(); Siege->Battlefield->TeamSpawns.Init(FVector(100,200,0),6);
    Bridge->MembershipPending.Add(Player->ScenarioCharacterId);
    State->SetCurrentZoneTrusted(TEXT("aegis_capital")); const FVector OriginalLocation=Replacement->GetActorLocation();
    TestTrue(TEXT("An unacknowledged capital baseline blocks preparation"),Bridge->HasPendingCapitalEnrollment());
    TestFalse(TEXT("Preparation cannot skip a capital player whose membership ACK is in flight"),Siege->StageCampaignParticipants(Error));
    TestTrue(TEXT("Preparation reports the acknowledgment barrier"),Error.Contains(TEXT("acknowledgments")));
    TestEqual(TEXT("Blocked preparation preserves the avatar position"),Replacement->GetActorLocation(),OriginalLocation);
    State->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
    TestFalse(TEXT("Remote pending seats do not block capital staging"),Bridge->HasPendingCapitalEnrollment());
    TestTrue(TEXT("Remote-only enrollment lets existing capital staging proceed"),Siege->StageCampaignParticipants(Error));
    TestEqual(TEXT("Remote enrollment never relocates a normal avatar"),Replacement->GetActorLocation(),OriginalLocation);
    Bridge->MembershipPending.Remove(Player->ScenarioCharacterId);
    Siege->bPreparing=false; Siege->Siege.Stage=1; Siege->Siege.Phase=EWarSiegePhase::Transition;
    TestTrue(TEXT("A durably approved transition seat enrolls natively"),Siege->Enroll(Player,Error));
    State->SetCurrentZoneTrusted(TEXT("aegis_capital")); State->SetScenarioTransferPending(true);
    Bridge->PendingAdmissions.Add(Player->ScenarioCharacterId,Player); Bridge->FinishAdmissions();
    TestTrue(TEXT("Unavailable actual capital entry remains pending"),Bridge->PendingAdmissions.Contains(Player->ScenarioCharacterId));
    TestTrue(TEXT("A late capital seat stays protected until validated staging"),State->IsScenarioTransferPending());
    TestEqual(TEXT("Failed late staging preserves the avatar position"),Replacement->GetActorLocation(),OriginalLocation);
    State->SetCurrentZoneTrusted(TEXT("dawnline_expanse")); Bridge->FinishAdmissions();
    TestFalse(TEXT("A remote approved seat releases its local transfer barrier"),State->IsScenarioTransferPending());
    TestFalse(TEXT("Remote seats finish without capital relocation"),Bridge->PendingAdmissions.Contains(Player->ScenarioCharacterId));
    TestEqual(TEXT("Remote seat release preserves the original position"),Replacement->GetActorLocation(),OriginalLocation);
    auto Recorded=MakeShared<FJsonObject>(); auto RecordedDocument=MakeShared<FJsonObject>();
    RecordedDocument->SetStringField(TEXT("zone"),TEXT("aegis_capital")); Recorded->SetObjectField(TEXT("document"),RecordedDocument);
    Bridge->ApprovedIds.Add(Player->ScenarioCharacterId);
    TestTrue(TEXT("An approved capital recovery must reenter through current-stage staging"),Bridge->StagesRecoveryAtEntry(Player->ScenarioCharacterId,Recorded));
    RecordedDocument->SetStringField(TEXT("zone"),TEXT("dawnline_expanse"));
    TestFalse(TEXT("A recorded remote recovery retains its saved position"),Bridge->StagesRecoveryAtEntry(Player->ScenarioCharacterId,Recorded));
    RecordedDocument->SetStringField(TEXT("zone"),TEXT("aegis_capital")); Bridge->ApprovedIds.Remove(Player->ScenarioCharacterId);
    TestFalse(TEXT("An unenrolled recovery is not admitted through siege staging"),Bridge->StagesRecoveryAtEntry(Player->ScenarioCharacterId,Recorded));
    auto Accepted=MakeShared<FJsonObject>(); Accepted->SetStringField(TEXT("activationId"),TEXT("accepted-before-controller-destroyed"));
    Accepted->SetStringField(TEXT("characterId"),TEXT("departed-stable-character")); Accepted->SetStringField(TEXT("realm"),TEXT("riftbound"));
    Bridge->Encounter=nullptr; Bridge->ReserveDisconnectedSeat(Accepted);
    TestEqual(TEXT("A departed accepted seat schedules a reservation without a current encounter"),Bridge->Requests.Num(),1);
    if (Bridge->Requests.Num()==1)
    {
        const auto Reservation=Bridge->Requests[0].Value;
        TestEqual(TEXT("Departed seat keeps the accepted activation identity"),Reservation->GetStringField(TEXT("activationId")),FString(TEXT("accepted-before-controller-destroyed")));
        TestEqual(TEXT("Departed seat keeps the accepted character identity"),Reservation->GetStringField(TEXT("characterId")),FString(TEXT("departed-stable-character")));
        TestEqual(TEXT("Departed seat keeps the accepted realm"),Reservation->GetStringField(TEXT("realm")),FString(TEXT("riftbound")));
        TestEqual(TEXT("Departed seat requests the bounded backend disconnect reservation"),Reservation->GetStringField(TEXT("action")),FString(TEXT("disconnect")));
        TestFalse(TEXT("Reservation has a stable request ID for transport retries"),Reservation->GetStringField(TEXT("requestId")).IsEmpty());
    }
    TestTrue(TEXT("The departed character requires recovery before further writes"),Bridge->PendingRecovery.Contains(TEXT("departed-stable-character")));
    auto ForeignLease=MakeShared<FJsonObject>(); ForeignLease->SetStringField(TEXT("hostId"),TEXT("another-native-host"));
    ForeignLease->SetStringField(TEXT("zoneId"),TEXT("aegis_capital")); Bridge->bOwnerLeaseReady=true;
    Bridge->ApplyLease(ForeignLease);
    TestNull(TEXT("A public foreign-host lease cannot create a local encounter"),Bridge->Encounter.Get());
    TestFalse(TEXT("Foreign ownership cannot authorize recovery admission"),Bridge->bOwnerLeaseReady);
    Bridge->Encounter=Siege; const auto RecordedPhase=Siege->Siege.Phase; const int32 RecordedStage=Siege->Siege.Stage;
    Bridge->ApplyLease(ForeignLease);
    TestTrue(TEXT("A foreign lease pauses existing admission before reconciliation"),Siege->bLeasePaused);
    TestEqual(TEXT("Foreign ownership never rewrites the local stage"),Siege->Siege.Stage,RecordedStage);
    TestEqual(TEXT("Foreign ownership never rewrites the recorded phase"),int32(Siege->Siege.Phase),int32(RecordedPhase));
    ForeignLease->SetStringField(TEXT("hostId"),Bridge->HostId); ForeignLease->SetStringField(TEXT("zoneId"),TEXT("riftspire_capital"));
    Siege->bLeasePaused=false; Bridge->ApplyLease(ForeignLease);
    TestTrue(TEXT("A matching host still rejects a different physical zone"),Siege->bLeasePaused);
    TestEqual(TEXT("Foreign-zone rejection retains the owning local encounter"),Bridge->Encounter.Get(),Siege);
    Bridge->Requests.Reset();Bridge->CheckpointQueued.Reset();Bridge->bBusy=true;
    State->SetSiegeMembership(nullptr);State->SetCurrentZoneTrusted(TEXT("aegis_capital"));State->SetScenarioTransferPending(true);
    Bridge->Characters.Add(Player->ScenarioCharacterId,Recorded);
    Bridge->Returns.Add(Player->ScenarioCharacterId,{Player,Siege->ActivationId});
    TestTrue(TEXT("Pending participant return remains visible to physical evacuation"),Bridge->IsCharacterReturnPending(Player));
    Bridge->Checkpoint(Player,true);
    TestFalse(TEXT("A pending participant return prevents evacuation from changing its canonical scope"),Bridge->CheckpointQueued.Contains(Player->ScenarioCharacterId));
    TestEqual(TEXT("Evacuation cannot queue ahead of the final participant return acknowledgment"),Bridge->Requests.Num(),0);
    Bridge->Returns.Remove(Player->ScenarioCharacterId);Bridge->CheckpointQueued.Reset();Bridge->Requests.Reset();
    TestFalse(TEXT("A completed return releases the evacuation deferral"),Bridge->IsCharacterReturnPending(Player));
    Bridge->Checkpoint(Player,true);
    TestEqual(TEXT("A completed participant return permits a later distinct capital evacuation"),Bridge->Requests.Num(),1);
    if (Bridge->Requests.Num()==1)
        TestEqual(TEXT("Later evacuation retains its explicit journal scope"),Bridge->Requests[0].Value->GetStringField(TEXT("scope")),FString(TEXT("evacuation")));
    Bridge->Requests.Reset();Bridge->CheckpointQueued.Reset();Bridge->Encounter=nullptr;Bridge->bOwnerLeaseReady=true;
    const FString Id=Player->ScenarioCharacterId,OriginalActivation=TEXT("original-recovery-custody");
    State->SetScenarioTransferPending(true);State->SetCurrentZoneTrusted(TEXT("dawnline_expanse"));
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),100);
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),100);
    const FVector ActualReturn(222,333,444);Replacement->SetActorLocation(ActualReturn);
    auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,TEXT("/Game/MigrationProof/Visual_civic_battle_prelate_m"));
    if (!TestTrue(TEXT("Return custody uses an actual ready native character visual"),Replacement->SetVisualDefinition(Visual,Error))) return false;
    auto RecoveryCharacter=Bridge->Capture(Player);
    if (!TestNotNull(TEXT("Ready native post-respawn character can be captured"),RecoveryCharacter.Get())) return false;
    auto OldRuntime=RecoveryCharacter->GetObjectField(TEXT("document"))->GetObjectField(TEXT("runtime"));
    OldRuntime->SetNumberField(TEXT("health"),0);OldRuntime->SetBoolField(TEXT("dead"),true);
    RecoveryCharacter->GetObjectField(TEXT("document"))->SetStringField(TEXT("zone"),TEXT("aegis_capital"));
    RecoveryCharacter->SetArrayField(TEXT("returnPosition"),{MakeShared<FJsonValueNumber>(9),MakeShared<FJsonValueNumber>(8),MakeShared<FJsonValueNumber>(7)});
    UWarCampaignSiegeSubsystem::FRecovery Recovery;
    Recovery.Player=Player;Recovery.Character=RecoveryCharacter;Recovery.Activation=OriginalActivation;
    Recovery.Revision=7;Recovery.WalSequence=3;Recovery.bPawnRestored=true;Recovery.bRespawnPending=true;Recovery.bSafeRelocation=true;
    Bridge->Recoveries.Add(Id,Recovery);Bridge->PendingRecovery.Add(Id);Bridge->RestoreRequested.Add(Id);
    Bridge->AcknowledgeRecovery(Id);
    TestEqual(TEXT("Restored recovery first queues exactly the ordinary document acknowledgment"),Bridge->Requests.Num(),1);
    if (Bridge->Requests.Num()!=1) return false;
    TestEqual(TEXT("Recovery acknowledgment uses the ordinary restored endpoint"),Bridge->Requests[0].Path,FString(TEXT("restored")));
    TestFalse(TEXT("A restore ACK cannot flag an old capital document as returned"),Bridge->Requests[0].Value->HasField(TEXT("returned")));
    auto RestoredAck=MakeShared<FJsonObject>();RestoredAck->SetNumberField(TEXT("version"),1);RestoredAck->SetStringField(TEXT("characterId"),Id);
    RestoredAck->SetNumberField(TEXT("revision"),7);RestoredAck->SetNumberField(TEXT("walSequence"),3);RestoredAck->SetBoolField(TEXT("recoveryPending"),false);
    auto RestoreRequest=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();
    auto WrongAck=MakeShared<FJsonObject>();WrongAck->SetNumberField(TEXT("version"),1);WrongAck->SetStringField(TEXT("characterId"),TEXT("different-character"));
    RestoreRequest.Reply(true,WrongAck,FString());
    TestTrue(TEXT("Malformed restore ACK keeps the original recovery custody"),Bridge->Recoveries.Contains(Id));
    TestTrue(TEXT("Malformed restore ACK cannot release ordinary movement"),State->IsScenarioTransferPending());
    Bridge->AcknowledgeRecovery(Id);
    if (Bridge->Requests.Num()!=1) return false;
    RestoreRequest=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();Bridge->ObserveAcks(RestoredAck);RestoreRequest.Reply(true,RestoredAck,FString());
    TestFalse(TEXT("Ordinary restored ACK completes only the restoration phase"),Bridge->PendingRecovery.Contains(Id));
    TestTrue(TEXT("Post-respawn relocation retains a separate full-document return barrier"),Bridge->IsCharacterReturnPending(Player));
    TestTrue(TEXT("Ordinary restored ACK keeps post-return movement held"),State->IsScenarioTransferPending());
    TestEqual(TEXT("Recovered return keeps its original owning activation"),Bridge->Returns[Id].Activation,OriginalActivation);
    TestFalse(TEXT("Recovered participant return cannot switch journal scope"),Bridge->Returns[Id].bEvacuation);
    Bridge->Checkpoint(Player,true);
    TestEqual(TEXT("Restored participant custody still defers a competing evacuation baseline"),Bridge->Requests.Num(),0);
    Bridge->FinishReturns();
    TestEqual(TEXT("Unready destination streaming cannot claim a safe durable return"),Bridge->Requests.Num(),0);
    // Exercise the same transport operation after its physical readiness gate, using actual
    // current pawn/PlayerState capture. This does not assert fixture floor or streaming approval.
    Bridge->SendReturnCheckpoint(Id);
    if (!TestEqual(TEXT("Full current return queues one durable checkpoint"),Bridge->Requests.Num(),1)) return false;
    auto ReturnRequest=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();
    const auto CurrentReturn=ReturnRequest.Value->GetObjectField(TEXT("character"));const auto CurrentDocument=CurrentReturn->GetObjectField(TEXT("document"));
    TestEqual(TEXT("Full return uses the original activation rather than a current/global encounter"),ReturnRequest.Value->GetStringField(TEXT("activationId")),OriginalActivation);
    TestEqual(TEXT("Full returned checkpoint preserves participant scope"),ReturnRequest.Value->GetStringField(TEXT("scope")),FString(TEXT("participant")));
    TestTrue(TEXT("Only the full actual document marks return complete"),ReturnRequest.Value->GetBoolField(TEXT("returned")));
    TestEqual(TEXT("Full return persists the actual relocated safe-zone document"),CurrentDocument->GetStringField(TEXT("zone")),FString(TEXT("dawnline_expanse")));
    const auto ReturnPosition=CurrentReturn->GetArrayField(TEXT("returnPosition"));
    TestEqual(TEXT("Full return persists actual post-relocation X"),ReturnPosition[0]->AsNumber(),ActualReturn.X);
    TestEqual(TEXT("Full return persists actual post-relocation Y"),ReturnPosition[1]->AsNumber(),ActualReturn.Y);
    TestEqual(TEXT("Full return persists actual post-relocation Z"),ReturnPosition[2]->AsNumber(),ActualReturn.Z);
    TestEqual(TEXT("Full return persists the actual normal respawn health"),CurrentDocument->GetObjectField(TEXT("runtime"))->GetNumberField(TEXT("health")),100.);
    TestFalse(TEXT("Full return cannot save the old defeated intent after a genuine respawn"),CurrentDocument->GetObjectField(TEXT("runtime"))->GetBoolField(TEXT("dead")));
    TestEqual(TEXT("Full return preserves existing persistent reward receipts"),CurrentDocument->GetObjectField(TEXT("runtime"))->GetArrayField(TEXT("rewards")).Num(),1);
    ReturnRequest.Reply(false,nullptr,TEXT("durable commit unavailable"));
    TestTrue(TEXT("Failed full return keeps movement protected"),State->IsScenarioTransferPending());
    TestTrue(TEXT("Failed full return retains original custody for retry"),Bridge->Returns.Contains(Id));
    Bridge->SendReturnCheckpoint(Id);if (Bridge->Requests.Num()!=1) return false;
    ReturnRequest=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();ReturnRequest.Reply(true,RestoredAck,FString());
    TestTrue(TEXT("An old restore revision cannot acknowledge a newer full return"),Bridge->Returns.Contains(Id));
    TestTrue(TEXT("Stale full-return ACK cannot release the character"),State->IsScenarioTransferPending());
    Bridge->SendReturnCheckpoint(Id);if (Bridge->Requests.Num()!=1) return false;
    ReturnRequest=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();RestoredAck->SetNumberField(TEXT("revision"),8);
    Bridge->ObserveAcks(RestoredAck);ReturnRequest.Reply(true,RestoredAck,FString());
    TestFalse(TEXT("Only the current full returned checkpoint ACK releases custody"),Bridge->Returns.Contains(Id));
    TestFalse(TEXT("Current full return ACK restores ordinary character movement"),State->IsScenarioTransferPending());
    TestEqual(TEXT("Return release restores the actual replacement movement mode"),uint8(Replacement->GetCharacterMovement()->MovementMode),uint8(MOVE_Walking));
    Bridge->Encounter=Siege;Bridge->ApprovedIds.Add(Id);Recovery.Activation=TEXT("old-visitor-activation");Recovery.bEvacuation=true;
    Recovery.Revision=8;Bridge->Recoveries.Add(Id,Recovery);Bridge->PendingRecovery.Add(Id);State->SetScenarioTransferPending(true);
    Bridge->AcknowledgeRecovery(Id);if (Bridge->Requests.Num()!=1) return false;
    RestoreRequest=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();RestoreRequest.Reply(true,RestoredAck,FString());
    TestTrue(TEXT("Visitor recovery preserves evacuation custody after its ordinary restore ACK"),Bridge->Returns[Id].bEvacuation);
    TestEqual(TEXT("Visitor recovery keeps its historical activation despite a new current encounter"),Bridge->Returns[Id].Activation,FString(TEXT("old-visitor-activation")));
    TestTrue(TEXT("Unrelated current opt-in cannot release a prior visitor return"),State->IsScenarioTransferPending());
    Bridge->Returns.Reset();Bridge->Encounter=nullptr;Bridge->ApprovedIds.Reset();
    Bridge->Returns.Add(Id,{Player,OriginalActivation});Bridge->SendReturnCheckpoint(Id);
    if (Bridge->Requests.Num()!=1) return false;
    auto InterruptedReturn=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();
    const auto ImmutableReturn=Bridge->Returns[Id].Document;
    auto* NewPlayer=World->SpawnActor<AWarPlayerController>();auto* NewState=World->SpawnActor<AWarPlayerState>();
    NewPlayer->PlayerState=NewState;NewState->SetOwner(NewPlayer);NewState->SetDevelopmentRealm(EWarRealm::Aegis);
    NewPlayer->ScenarioCharacterId=Id;NewPlayer->bCampaignIdentityProvisioned=true;
    auto* NewPawn=World->SpawnActor<AWarCharacter>();NewPawn->SetPlayerState(NewState);NewPlayer->Possess(NewPawn);
    NewPawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);NewState->SetCurrentZoneTrusted(TEXT("riftspire_capital"));
    if (!TestTrue(TEXT("Replacement-controller fixture owns an actual ready native pawn"),NewPawn->SetVisualDefinition(Visual,Error))) return false;
    Player->Destroy();
    TestFalse(TEXT("Same-ID replacement is not admitted during a pending return"),Bridge->PrepareCharacter(NewPlayer));
    TestEqual(TEXT("Return custody rebinds the actual replacement controller"),Bridge->Returns[Id].Player.Get(),NewPlayer);
    TestTrue(TEXT("Replacement default state remains transfer-held"),NewState->IsScenarioTransferPending());
    TestEqual(TEXT("Replacement controller cannot move its fresh default pawn"),uint8(NewPawn->GetCharacterMovement()->MovementMode),uint8(MOVE_None));
    TestEqual(TEXT("Rebinding preserves the immutable actual old pawn return document"),Bridge->Returns[Id].Document.Get(),ImmutableReturn.Get());
    InterruptedReturn.Reply(false,nullptr,TEXT("interrupted final return commit"));
    TestTrue(TEXT("Failed old-controller return retains replacement custody"),Bridge->Returns[Id].bRebinding);
    Bridge->SendReturnCheckpoint(Id);if (Bridge->Requests.Num()!=1) return false;
    InterruptedReturn=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();
    const auto RetryDocument=InterruptedReturn.Value->GetObjectField(TEXT("character"))->GetObjectField(TEXT("document"));
    TestEqual(TEXT("Replacement retry preserves original actual zone, never its fresh defaults"),RetryDocument->GetStringField(TEXT("zone")),FString(TEXT("dawnline_expanse")));
    TestEqual(TEXT("Replacement retry preserves original post-respawn health"),RetryDocument->GetObjectField(TEXT("runtime"))->GetNumberField(TEXT("health")),100.);
    TestEqual(TEXT("Replacement retry preserves original activation custody"),InterruptedReturn.Value->GetStringField(TEXT("activationId")),OriginalActivation);
    RestoredAck->SetNumberField(TEXT("revision"),9);Bridge->ObserveAcks(RestoredAck);InterruptedReturn.Reply(true,RestoredAck,FString());
    TestTrue(TEXT("Durable return ACK does not admit an unrestored replacement pawn"),NewState->IsScenarioTransferPending());
    TestTrue(TEXT("Replacement custody retains its committed document until actual safe restoration"),Bridge->Returns.Contains(Id) && Bridge->Returns[Id].bCommitted);
    TestFalse(TEXT("Unavailable replacement restoration remains recoverably held"),Bridge->PrepareCharacter(NewPlayer));
    TestEqual(TEXT("Unready handoff does not overwrite the fresh controller with invented defaults"),NewState->GetCurrentZone(),FName(TEXT("riftspire_capital")));
    TestEqual(TEXT("Unready handoff preserves the actual old-document zone"),Bridge->Returns[Id].Document->GetObjectField(TEXT("document"))->GetStringField(TEXT("zone")),FString(TEXT("dawnline_expanse")));
    Recovery.Player=NewPlayer;Recovery.Character=ImmutableReturn;Recovery.Activation=OriginalActivation;
    Recovery.bEvacuation=false;Recovery.bReturnHandoff=true;Bridge->Recoveries.Add(Id,Recovery);
    TestTrue(TEXT("Trusted same-context handoff permits RestartPlayer to create its held avatar"),Bridge->PrepareCharacter(NewPlayer));
    TestTrue(TEXT("A permitted recovery spawn still holds all ordinary character mutations"),NewState->IsScenarioTransferPending());
    Bridge->Recoveries[Id].Activation=TEXT("another-activation");
    TestFalse(TEXT("A different-context recovery cannot spawn a default replacement"),Bridge->PrepareCharacter(NewPlayer));
    Bridge->Recoveries[Id].Activation=OriginalActivation;Bridge->Recoveries[Id].bEvacuation=true;
    TestFalse(TEXT("A different-scope recovery cannot authorize replacement spawning"),Bridge->PrepareCharacter(NewPlayer));
    Bridge->Recoveries[Id].bEvacuation=false;Bridge->Recoveries[Id].bReturnHandoff=false;
    TestTrue(TEXT("Real durable restore fallback also permits its initialized held avatar"),Bridge->PrepareCharacter(NewPlayer));
    Bridge->Recoveries.Remove(Id);Bridge->Returns[Id].bRebinding=false;
    TestTrue(TEXT("The same authoritative PlayerState may respawn normally while returning"),Bridge->PrepareCharacter(NewPlayer));
    TestTrue(TEXT("Same-controller normal respawn retains the final return hold"),NewState->IsScenarioTransferPending());
    Bridge->Returns.Remove(Id);Bridge->Encounter=Siege;Siege->ActivationId=OriginalActivation;Bridge->ApprovedIds.Add(Id);
    Recovery.Player=NewPlayer;Recovery.Character=ImmutableReturn;Recovery.Activation=OriginalActivation;Recovery.bEvacuation=false;
    Recovery.bAcknowledging=false;Recovery.bPawnRestored=true;Recovery.bReturnHandoff=false;Recovery.Revision=9;
    Bridge->Recoveries.Add(Id,Recovery);Bridge->PendingRecovery.Add(Id);Bridge->RestoreRequested.Add(Id);
    Bridge->AcknowledgeRecovery(Id);if (Bridge->Requests.Num()!=1) return false;
    RestoreRequest=MoveTemp(Bridge->Requests[0]);Bridge->Requests.Reset();NewPlayer->Destroy();RestoreRequest.Reply(true,RestoredAck,FString());
    TestTrue(TEXT("Controller disappearance during active restore ACK retains recovery admission protection"),Bridge->PendingRecovery.Contains(Id));
    TestFalse(TEXT("An expired controller cannot retain a stale completed restore request"),Bridge->RestoreRequested.Contains(Id));
    TestFalse(TEXT("An expired active recovery cannot authorize a fresh default avatar"),Bridge->Recoveries.Contains(Id));
    auto* Reconnected=World->SpawnActor<AWarPlayerController>();auto* ReconnectedState=World->SpawnActor<AWarPlayerState>();
    Reconnected->PlayerState=ReconnectedState;ReconnectedState->SetOwner(Reconnected);ReconnectedState->SetDevelopmentRealm(EWarRealm::Aegis);
    Reconnected->ScenarioCharacterId=Id;Reconnected->bCampaignIdentityProvisioned=true;
    TestFalse(TEXT("Late active-member reconnect must recover the durable document again"),Bridge->PrepareCharacter(Reconnected));
    TestTrue(TEXT("Late active-member reconnect never releases a default PlayerState"),ReconnectedState->IsScenarioTransferPending());
    return !HasAnyErrors();
}
#endif
