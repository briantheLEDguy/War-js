#include "WarCampaignSiegeSubsystem.h"
#include "WarSiegeEncounter.h"
#include "WarScenarioTransport.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCityDefinition.h"
#include "WarZoneStreamingSubsystem.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "EngineUtils.h"
#include "WarCharacter.h"
#include "WarAttributeSet.h"
#include "WarSiegeNavigation.h"
#include "WarZoneAnchor.h"
#include "Components/CapsuleComponent.h"
#include "AbilitySystemComponent.h"
#include "JsonObjectConverter.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/SecureHash.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/FileManager.h"

namespace
{
    bool StableCharacterId(const FString& Id)
    {
        if (Id.IsEmpty() || Id.Len() > 100 || Id == TEXT("__proto__") || Id == TEXT("constructor") || Id == TEXT("prototype")) return false;
        for (TCHAR C : Id) if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '_' || C == '-')) return false;
        return true;
    }
}

bool UWarCampaignSiegeSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{ return Type == EWorldType::Game || Type == EWorldType::PIE; }
TStatId UWarCampaignSiegeSubsystem::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCampaignSiegeSubsystem, STATGROUP_Tickables); }
void UWarCampaignSiegeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    FString File;
    if (UE_BUILD_SHIPPING || !FParse::Value(FCommandLine::Get(), TEXT("WarCampaignSiegeHostConfig="), File)) return;
    const auto Config = WarScenarioTransport::ReadConfig(File);
    if (!Config || !Config->TryGetStringField(TEXT("url"), Url) || !Config->TryGetStringField(TEXT("key"), BootstrapKey)
        || !Config->TryGetStringField(TEXT("hostId"), HostId)) Url.Reset();
    if (Url.IsEmpty()) return;
    Config->TryGetStringField(TEXT("characterId"),ProvisionedCharacterId);
    const FTCHARToUTF8 Host(*HostId); uint8 Digest[20]; FSHA1::HashBuffer(Host.Get(),Host.Length(),Digest);
    WalDirectory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("CampaignSiege/Wal")/BytesToHex(Digest,20).ToLower());
    TArray<FString> Files; IFileManager::Get().FindFiles(Files,*(WalDirectory/TEXT("*.json")),true,false);
    for (const FString& Name : Files)
    {
        const FString Filename = WalDirectory/Name; auto Record = WarScenarioTransport::ReadConfig(Filename);
        const TSharedPtr<FJsonObject>* Value = nullptr; FString Owner, Id, Activation, RequestId; double Version = 0, Base = 0, SequenceNumber = 0;
        if (!Record || !Record->TryGetNumberField(TEXT("schemaVersion"),Version) || Version != 1
            || !Record->TryGetStringField(TEXT("hostId"),Owner) || Owner != HostId || !Record->TryGetObjectField(TEXT("body"),Value)
            || !(*Value)->TryGetStringField(TEXT("characterId"),Id) || !StableCharacterId(Id)
            || !(*Value)->TryGetStringField(TEXT("activationId"),Activation) || Activation.IsEmpty()
            || !(*Value)->TryGetStringField(TEXT("requestId"),RequestId) || RequestId.IsEmpty()
            || !(*Value)->TryGetNumberField(TEXT("baseRevision"),Base) || Base < 1 || Base > MAX_int32 || FMath::FloorToDouble(Base) != Base
            || !(*Value)->TryGetNumberField(TEXT("walSequence"),SequenceNumber) || SequenceNumber < 1 || SequenceNumber > MAX_int32 || FMath::FloorToDouble(SequenceNumber) != SequenceNumber
            || !(*Value)->HasTypedField<EJson::Object>(TEXT("character")) || LocalWals.Contains(Id))
        { WalError = TEXT("A private character mutation WAL is corrupt or duplicated. Keep its files for protected recovery."); continue; }
        LocalWals.Add(Id,{Filename,*Value}); PendingRecovery.Add(Id);
    }
}
TSharedPtr<FJsonObject> UWarCampaignSiegeSubsystem::Body(bool Activation) const
{
    auto Value = MakeShared<FJsonObject>(); Value->SetStringField(TEXT("hostId"), HostId);
    Value->SetStringField(TEXT("requestId"), FGuid::NewGuid().ToString(EGuidFormats::Digits));
    if (Activation && Encounter) Value->SetStringField(TEXT("activationId"), Encounter->ActivationId);
    return Value;
}
void UWarCampaignSiegeSubsystem::Request(const FString& Path, TSharedPtr<FJsonObject> Value,
    TFunction<void(bool,TSharedPtr<FJsonObject>,FString)> Reply)
{
    if (bBusy) { Requests.Add({Path, Value, MoveTemp(Reply)}); return; }
    auto Retry = MakeShared<FQueuedRequest>(FQueuedRequest{Path, Value, MoveTemp(Reply)});
    bBusy = true; const TWeakObjectPtr<UWarCampaignSiegeSubsystem> Weak = this;
    WarScenarioTransport::Request(Url, Token.IsEmpty() ? BootstrapKey : Token, TEXT("POST"), TEXT("/native/siege/") + Path, Value,
        [Weak,Retry](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) mutable {
        if (auto* Self = Weak.Get())
        {
            Self->bBusy = false;
            if (!Ok && Error.Contains(TEXT("Scenario host unavailable")))
            { Self->RetryAt = Self->GetWorld()->GetTimeSeconds()+2; Self->Requests.Insert(MoveTemp(*Retry),0); return; }
            if (Ok) Self->ObserveAcks(Data);
            Retry->Reply(Ok, Data, Error);
        }
    });
}
TSharedPtr<FJsonObject> UWarCampaignSiegeSubsystem::Snapshot(const FWarSiegeState& S, bool Preparing, double PreparationRemaining)
{
    auto Value = MakeShared<FJsonObject>(); Value->SetNumberField(TEXT("stage"), S.Stage);
    const FString Phase = Preparing ? TEXT("preparing") : S.Phase == EWarSiegePhase::Active ? TEXT("active")
        : S.Phase == EWarSiegePhase::Transition ? TEXT("transition") : S.Phase == EWarSiegePhase::Finished ? TEXT("finished") : TEXT("preparing");
    Value->SetStringField(TEXT("phase"), Phase);
    TArray<TSharedPtr<FJsonValue>> Main, Optional;
    for (int32 I = 0; I < 8; ++I) if (S.MainClaims & (1 << I)) Main.Add(MakeShared<FJsonValueNumber>(I));
    for (int32 I = 0; I < 3; ++I) if (S.OptionalClaims & (1 << I)) Optional.Add(MakeShared<FJsonValueNumber>(I));
    Value->SetArrayField(TEXT("completed"), Main); Value->SetArrayField(TEXT("optionalCompleted"), Optional);
    Value->SetNumberField(TEXT("elapsed"), S.Elapsed);
    Value->SetNumberField(TEXT("remaining"), (Preparing || S.Phase == EWarSiegePhase::Active) && !S.bOvertime ? S.Remaining : 0);
    Value->SetNumberField(TEXT("transitionRemaining"), S.Phase == EWarSiegePhase::Transition ? S.Remaining : 0);
    Value->SetNumberField(TEXT("overtimeRemaining"), S.bOvertime ? S.Remaining : (Preparing || S.Phase == EWarSiegePhase::Active) ? WarSiege::OvertimeSeconds : 0);
    Value->SetNumberField(TEXT("preparationRemaining"), Preparing ? FMath::Clamp(PreparationRemaining, 0., 180.) : 0);
    Value->SetNumberField(TEXT("progress"), S.Progress); Value->SetNumberField(TEXT("leftProgress"), S.LeftProgress);
    Value->SetNumberField(TEXT("rightProgress"), S.RightProgress); Value->SetNumberField(TEXT("optionalProgress"), S.OptionalProgress);
    Value->SetNumberField(TEXT("absence"), S.Absence); Value->SetNumberField(TEXT("leftAbsence"), S.LeftAbsence);
    Value->SetNumberField(TEXT("rightAbsence"), S.RightAbsence); Value->SetNumberField(TEXT("optionalAbsence"), S.OptionalAbsence);
    Value->SetNumberField(TEXT("overtimeAbsence"), S.OvertimeAbsence); Value->SetNumberField(TEXT("contestedSeconds"), S.ContestedSeconds);
    TArray<TSharedPtr<FJsonValue>> Times; for (double Time : S.MilestoneSeconds) Times.Add(MakeShared<FJsonValueNumber>(Time));
    Value->SetArrayField(TEXT("milestoneSeconds"), Times);
    if (S.Phase == EWarSiegePhase::Finished) Value->SetBoolField(TEXT("attackersWon"), S.bAttackersWon);
    return Value;
}
bool UWarCampaignSiegeSubsystem::RestoreSnapshot(const TSharedPtr<FJsonObject>& Json, FWarSiegeState& State, FString& Error)
{
    if (!Json) { Error = TEXT("Missing native siege snapshot."); return false; }
    FString Phase; double Stage = 0, Elapsed = 0, Remaining = 0, Transition = 0, Overtime = 0;
    const TArray<TSharedPtr<FJsonValue>>* Main = nullptr; const TArray<TSharedPtr<FJsonValue>>* Optional = nullptr;
    if (!Json->TryGetStringField(TEXT("phase"), Phase) || !Json->TryGetNumberField(TEXT("stage"), Stage)
        || Stage < 0 || Stage > 2 || FMath::FloorToDouble(Stage) != Stage
        || !Json->TryGetArrayField(TEXT("completed"), Main) || !Json->TryGetArrayField(TEXT("optionalCompleted"), Optional)
        || !Json->TryGetNumberField(TEXT("elapsed"), Elapsed) || !Json->TryGetNumberField(TEXT("remaining"), Remaining)
        || !Json->TryGetNumberField(TEXT("transitionRemaining"), Transition) || !Json->TryGetNumberField(TEXT("overtimeRemaining"), Overtime))
    { Error = TEXT("Invalid native siege snapshot."); return false; }
    FWarSiegeState Restored; Restored.Capacity = 18; Restored.RulesVersion = 2; Restored.Stage = int32(Stage);
    for (const auto& Value : *Main)
    { double Index = 0; if (!Value->TryGetNumber(Index) || Index < 0 || Index > 7 || FMath::FloorToDouble(Index) != Index) return false; Restored.MainClaims |= 1 << int32(Index); }
    for (const auto& Value : *Optional)
    { double Index = 0; if (!Value->TryGetNumber(Index) || Index < 0 || Index > 2 || FMath::FloorToDouble(Index) != Index) return false; Restored.OptionalClaims |= 1 << int32(Index); }
    for (double Number : {Elapsed,Remaining,Transition,Overtime}) if (!FMath::IsFinite(Number) || Number < 0) return false;
    if (Elapsed > 3001 || Remaining > WarSiege::StageSeconds || Transition > WarSiege::TransitionSeconds || Overtime > WarSiege::OvertimeSeconds) return false;
    Restored.Elapsed = Elapsed; Restored.bOvertime = Phase == TEXT("active") && Remaining <= 0 && Overtime > 0;
    Restored.Phase = Phase == TEXT("preparing") ? EWarSiegePhase::Waiting : Phase == TEXT("active") ? EWarSiegePhase::Active
        : Phase == TEXT("transition") ? EWarSiegePhase::Transition : Phase == TEXT("finished") ? EWarSiegePhase::Finished : EWarSiegePhase::Waiting;
    if (Phase != TEXT("preparing") && Phase != TEXT("active") && Phase != TEXT("transition") && Phase != TEXT("finished")) return false;
    Restored.Remaining = Restored.Phase == EWarSiegePhase::Transition ? Transition : Restored.bOvertime ? Overtime : Remaining;
    if (Restored.Stage == 0) { while (Restored.Objective < 3 && (Restored.MainClaims & (1 << Restored.Objective))) ++Restored.Objective; }
    else if (Restored.Stage == 1) Restored.Objective = WarSiege::CenterUnlocked(Restored) ? 2 : ((Restored.MainClaims & 0x10) ? 1 : 0);
    Restored.LeftProgress = (Restored.MainClaims & 0x10) ? 1 : 0; Restored.RightProgress = (Restored.MainClaims & 0x20) ? 1 : 0;
    Restored.bOptionalComplete = (Restored.OptionalClaims & (1 << Restored.Stage)) != 0; Restored.OptionalProgress = Restored.bOptionalComplete ? 1 : 0;
    if (Restored.Phase == EWarSiegePhase::Finished && !Json->TryGetBoolField(TEXT("attackersWon"), Restored.bAttackersWon)) return false;
    if (Restored.bAttackersWon && Restored.MainClaims != 0xff) return false;
    if ((Restored.Stage >= 1 && (Restored.MainClaims & 0x0f) != 0x0f)
        || (Restored.Stage >= 2 && (Restored.MainClaims & 0x70) != 0x70)
        || ((Restored.MainClaims & 0x40) && !WarSiege::CenterUnlocked(Restored))
        || ((Restored.MainClaims & 0x80) && !Restored.bAttackersWon)) return false;
    const auto Read = [&](const TCHAR* Key, double& Number, double Maximum) {
        double Value = 0; if (!Json->TryGetNumberField(Key, Value)) return true;
        if (!FMath::IsFinite(Value) || Value < 0 || Value > Maximum) return false; Number = Value; return true;
    };
    double Progress = Restored.Progress, Left = Restored.LeftProgress, Right = Restored.RightProgress, OptionalProgress = Restored.OptionalProgress;
    if (!Read(TEXT("progress"), Progress, 1) || !Read(TEXT("leftProgress"), Left, 1) || !Read(TEXT("rightProgress"), Right, 1)
        || !Read(TEXT("optionalProgress"), OptionalProgress, 1) || !Read(TEXT("absence"), Restored.Absence, 3000)
        || !Read(TEXT("leftAbsence"), Restored.LeftAbsence, 3000) || !Read(TEXT("rightAbsence"), Restored.RightAbsence, 3000)
        || !Read(TEXT("optionalAbsence"), Restored.OptionalAbsence, 3000) || !Read(TEXT("overtimeAbsence"), Restored.OvertimeAbsence, 120)
        || !Read(TEXT("contestedSeconds"), Restored.ContestedSeconds, 3000)) return false;
    Restored.Progress = Progress; Restored.LeftProgress = Left; Restored.RightProgress = Right; Restored.OptionalProgress = OptionalProgress;
    const TArray<TSharedPtr<FJsonValue>>* Times = nullptr;
    if (Json->TryGetArrayField(TEXT("milestoneSeconds"), Times)) for (const auto& Time : *Times)
    { double Value = 0; if (!Time->TryGetNumber(Value) || !FMath::IsFinite(Value) || Value < 0 || Value > Restored.Elapsed) return false; Restored.MilestoneSeconds.Add(Value); }
    State = Restored; return true;
}
namespace
{
    TSharedPtr<FJsonObject> CloneCharacter(const TSharedPtr<FJsonObject>& Source)
    {
        if (!Source) return nullptr;
        FString Text; TSharedPtr<FJsonObject> Copy;
        FJsonSerializer::Serialize(Source.ToSharedRef(), TJsonWriterFactory<>::Create(&Text));
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Copy); return Copy;
    }
    double EpochSeconds()
    { return double((FDateTime::UtcNow() - FDateTime(1970,1,1)).GetTicks()) / ETimespan::TicksPerSecond; }
    bool ReturnedCharacterAck(const TSharedPtr<FJsonObject>& Ack, const FString& Id, int32 MinimumRevision,
        int32 WalSequence, bool ExactRevision, FString& Error)
    {
        FString AckId; double Version = 0, AckRevision = 0, AckSequence = 0; bool Pending = true;
        if (!Ack || !Ack->TryGetNumberField(TEXT("version"), Version) || Version != 1
            || !Ack->TryGetStringField(TEXT("characterId"), AckId) || AckId != Id
            || !Ack->TryGetNumberField(TEXT("revision"), AckRevision) || !FMath::IsFinite(AckRevision)
            || AckRevision < MinimumRevision || AckRevision > MAX_int32 || FMath::FloorToDouble(AckRevision) != AckRevision
            || (ExactRevision && AckRevision != MinimumRevision)
            || !Ack->TryGetNumberField(TEXT("walSequence"), AckSequence) || AckSequence != WalSequence
            || !Ack->TryGetBoolField(TEXT("recoveryPending"), Pending) || Pending)
        { Error = TEXT("The character return acknowledgment does not match its durable revision. Recovery remains protected."); return false; }
        return true;
    }
}
TSharedPtr<FJsonObject> UWarCampaignSiegeSubsystem::Capture(AWarPlayerController* Player)
{
    if (!Player || Player->ScenarioCharacterId.IsEmpty() || PendingRecovery.Contains(Player->ScenarioCharacterId)) return nullptr;
    FString CaptureError;
    auto Value = WarScenarioTransport::Capture(Player, Player->ScenarioCharacterId, true, true, &CaptureError);
    if (!CaptureError.IsEmpty()) { Player->ClientZoneTravelStatus(CaptureError); return nullptr; }
    if (!Value)
    {
        // A death unpossesses the avatar. Preserve its trusted visual/location and refresh the
        // PlayerState document rather than inventing a different character or living health.
        Value = CloneCharacter(Characters.FindRef(Player->ScenarioCharacterId));
        auto* PS = Player->GetPlayerState<AWarPlayerState>();
        if (!Value || !PS) return nullptr;
        auto Document = Value->GetObjectField(TEXT("document")); auto Inventory = MakeShared<FJsonObject>();
        FJsonObjectConverter::UStructToJsonObject(FWarInventorySnapshot::StaticStruct(), &PS->GetInventory(), Inventory, 0, 0);
        Document->SetObjectField(TEXT("inventory"), Inventory); Document->SetStringField(TEXT("zone"), PS->GetCurrentZone().ToString());
        auto Runtime = PS->CaptureCampaignState(CaptureError);
        if (!Runtime) { Player->ClientZoneTravelStatus(CaptureError); return nullptr; }
        Runtime->SetBoolField(TEXT("dead"), !Player->GetPawn() || PS->GetAttributes()->GetHealth() <= 0);
        Document->SetObjectField(TEXT("runtime"), Runtime);
    }
    Characters.Add(Player->ScenarioCharacterId, CloneCharacter(Value)); return Value;
}
TArray<TSharedPtr<FJsonValue>> UWarCampaignSiegeSubsystem::CaptureMembers()
{
    TArray<TSharedPtr<FJsonValue>> Values;
    if (!LocalWals.IsEmpty()) return Values;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PC = Cast<AWarPlayerController>(It->Get()); PC && ConnectedIds.Contains(PC->ScenarioCharacterId))
            if (auto Character = Capture(PC)) Values.Add(MakeShared<FJsonValueObject>(Character));
    return Values;
}
void UWarCampaignSiegeSubsystem::ObserveRecovery(const TSharedPtr<FJsonObject>& Data)
{
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!Data || !Data->TryGetArrayField(TEXT("characterRecovery"), Rows)) return;
    for (const auto& Value : *Rows)
    {
        const auto Row = Value->AsObject(); FString Id; bool Pending = false;
        if (Row && Row->TryGetStringField(TEXT("characterId"), Id) && Row->TryGetBoolField(TEXT("recoveryPending"), Pending) && Pending)
            PendingRecovery.Add(Id);
    }
}
void UWarCampaignSiegeSubsystem::Recover(AWarPlayerController* Player)
{
    if (!bOwnerLeaseReady || !Player || LocalWals.Contains(Player->ScenarioCharacterId) || !PendingRecovery.Contains(Player->ScenarioCharacterId) || RestoreRequested.Contains(Player->ScenarioCharacterId)) return;
    const FString Id = Player->ScenarioCharacterId; RestoreRequested.Add(Id);
    if (auto* PS = Player->GetPlayerState<AWarPlayerState>()) PS->SetScenarioTransferPending(true);
    auto Value = Body(); Value->SetStringField(TEXT("characterId"), Id);
    const TWeakObjectPtr<AWarPlayerController> Weak = Player;
    Request(TEXT("restore"), Value, [this,Id,Weak](bool Ok,TSharedPtr<FJsonObject> Record,FString Error) {
        auto* PC = Weak.Get(); double Version = 0, Revision = 0, WalSequence = 0;
        FString Owner, RecordId, Activation, Scope, CharacterId; bool Pending = false, Returned = true, RespawnPending = false;
        const TSharedPtr<FJsonObject>* Character = nullptr;
        if (!Ok || !PC || !Record || !Record->TryGetNumberField(TEXT("version"), Version) || Version != 1
            || !Record->TryGetStringField(TEXT("hostId"), Owner) || Owner != HostId
            || !Record->TryGetStringField(TEXT("characterId"), RecordId) || RecordId != Id
            || !Record->TryGetStringField(TEXT("activationId"), Activation) || Activation.IsEmpty()
            || !Record->TryGetStringField(TEXT("scope"), Scope) || (Scope != TEXT("participant") && Scope != TEXT("evacuation"))
            || !Record->TryGetNumberField(TEXT("revision"), Revision) || !FMath::IsFinite(Revision)
            || Revision < 1 || Revision > MAX_int32 || FMath::FloorToDouble(Revision) != Revision
            || !Record->TryGetBoolField(TEXT("recoveryPending"), Pending) || !Pending
            || !Record->TryGetBoolField(TEXT("returned"), Returned) || Returned
            || !Record->TryGetBoolField(TEXT("respawnPending"), RespawnPending)
            || !Record->TryGetObjectField(TEXT("character"), Character)
            || !(*Character)->TryGetStringField(TEXT("id"), CharacterId) || CharacterId != Id)
        { RestoreRequested.Remove(Id); if (PC) PC->ClientZoneTravelStatus(Error.IsEmpty() ? TEXT("Character recovery is waiting for its durable document.") : Error); return; }
        Record->TryGetNumberField(TEXT("walSequence"), WalSequence);
        if (!FMath::IsFinite(WalSequence) || WalSequence < 0 || WalSequence > MAX_int32 || FMath::FloorToDouble(WalSequence) != WalSequence)
        { RestoreRequested.Remove(Id); PC->ClientZoneTravelStatus(TEXT("Character recovery is waiting for its durable WAL sequence.")); return; }
        FRecovery Recovery; Recovery.Player = PC; Recovery.Character = *Character; Recovery.Activation = Activation;
        Recovery.Revision = int32(Revision); Recovery.WalSequence = int32(WalSequence); Recovery.bEvacuation = Scope == TEXT("evacuation");
        Recovery.bRespawnPending = RespawnPending;
        const bool ActiveMember = !Recovery.bEvacuation && Encounter && Encounter->ActivationId == Activation && ApprovedIds.Contains(Id);
        Recovery.bSafeRelocation = !ActiveMember;
        // Only this recovering avatar is replaced; unrelated players continue normally.
        if (APawn* Pawn = PC->GetPawn()) { PC->UnPossess(); Pawn->Destroy(); }
        if (!WarScenarioTransport::Restore(PC, *Character, false, Error))
        { RestoreRequested.Remove(Id); PC->ClientZoneTravelStatus(Error); return; }
        Recoveries.Add(Id, MoveTemp(Recovery)); Characters.Add(Id, CloneCharacter(*Character));
        if (ActiveMember) { FString JoinError; Encounter->Enroll(PC, JoinError, true); }
        if (auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>()) Mode->RestartPlayer(PC);
    });
}
bool UWarCampaignSiegeSubsystem::ResolveRecoverySpawn(AWarPlayerController* Player,FTransform& Transform,bool& bRecovering,FString& Error) const
{
    const auto* Recovery=Player ? Recoveries.Find(Player->ScenarioCharacterId) : nullptr;
    bRecovering=Recovery && Recovery->Player.Get()==Player;
    if (!bRecovering) return true;
    const auto* PS=Player->GetPlayerState<AWarPlayerState>();
    const auto* Streaming=GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!bOwnerLeaseReady || !PS || !Recovery->Character || !Streaming
        || !Streaming->IsZoneReady(PS->GetCurrentZone(),Player))
    { Error=TEXT("Character recovery is waiting for authoritative ownership and its ready scene.");return false; }
    FVector Center;
    if (!Recovery->bReturnHandoff && !Recovery->bEvacuation && Encounter && Encounter->ActivationId==Recovery->Activation
        && ApprovedIds.Contains(Player->ScenarioCharacterId) && StagesRecoveryAtEntry(Player->ScenarioCharacterId,Recovery->Character))
    {
        if (!Encounter->FindCampaignSpawnCenter(Player,Center,Error,true)) return false;
    }
    else
    {
        const TSharedPtr<FJsonObject>* Document=nullptr;const TArray<TSharedPtr<FJsonValue>>* Position=nullptr;
        FString Zone;
        if (!Recovery->Character->TryGetObjectField(TEXT("document"),Document)
            || !(*Document)->TryGetStringField(TEXT("zone"),Zone)) return false;
        FVector Anchor;
        if (Zone==PS->GetCurrentZone().ToString())
        {
            if (!Recovery->Character->TryGetArrayField(TEXT("returnPosition"),Position) || Position->Num()!=3) return false;
            double Coordinates[3];
            for (int32 I=0;I<3;++I) if (!(*Position)[I]->TryGetNumber(Coordinates[I]) || !FMath::IsFinite(Coordinates[I])) return false;
            Anchor=FVector(Coordinates[0],Coordinates[1],Coordinates[2]);
        }
        else if (Recovery->bSafeRelocation)
        {
            const auto* Destination=AWarZoneAnchor::FindById(GetWorld(),PS->GetCurrentZone());
            if (!Destination) return false;Anchor=Destination->GetActorLocation();
        }
        else return false;
        if (!WarSiegeNavigation::SpawnCenter(GetWorld(),Anchor,Center))
        { Error=TEXT("Character recovery is waiting for clear recorded arrival space.");return false; }
    }
    Transform.SetLocation(Center);return true;
}

void UWarCampaignSiegeSubsystem::FinishRecoveries()
{
    if (!bOwnerLeaseReady) return;
    TArray<FString> FinishedHandoffs;
    for (auto& Row : Recoveries)
    {
        auto& Recovery = Row.Value; auto* PC = Recovery.Player.Get();
        auto* PS = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr; auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
        if (!PS || !Pawn || !Pawn->IsVisualReady() || Recovery.bAcknowledging) continue;
        auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
        if (!Streaming || !Streaming->IsZoneReady(PS->GetCurrentZone(), PC)) continue;
        const auto Document = Recovery.Character->GetObjectField(TEXT("document"));
        if (!Recovery.bPawnRestored)
        {
            const auto Position = Recovery.Character->GetArrayField(TEXT("returnPosition"));
            if (!Recovery.bReturnHandoff && !Recovery.bEvacuation && Encounter && Encounter->ActivationId == Recovery.Activation && StagesRecoveryAtEntry(Row.Key, Recovery.Character))
            {
                FString Error;
                if (!Encounter->StageCampaignParticipant(PC, Error, true)) { PC->ClientZoneTravelStatus(Error); continue; }
            }
            else if (!Recovery.bRespawnPending && !(Recovery.bSafeRelocation && Document->GetStringField(TEXT("zone")) != PS->GetCurrentZone().ToString()))
            {
                if (Position.Num() != 3) continue;
                const FVector Saved(Position[0]->AsNumber(),Position[1]->AsNumber(),Position[2]->AsNumber());
                const auto* Zone = AWarZoneAnchor::FindAt(GetWorld(), Saved);
                if (!Zone || Zone->ZoneId != PS->GetCurrentZone()) continue;
                FVector Center; const auto* Capsule = Pawn->GetCapsuleComponent();
                const bool Safe = WarSiegeNavigation::SpawnCandidate(GetWorld(), Saved-FVector(0,0,Capsule->GetScaledCapsuleHalfHeight()+3),
                    Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight(), Center, Pawn);
                const bool Moved = Safe && Pawn->TeleportTo(Center, Pawn->GetActorRotation());
                if (!Moved) continue;
            }
            auto Runtime = CloneCharacter(Document->GetObjectField(TEXT("runtime")));
            if (Recovery.bRespawnPending)
            { Runtime->SetNumberField(TEXT("health"), PS->GetAttributes()->GetMaxHealth()); Runtime->SetNumberField(TEXT("mana"), PS->GetAttributes()->GetMaxMana()); }
            FString RuntimeError;
            if (!PS->RestoreCampaignState(Runtime,RuntimeError,Recovery.bRespawnPending))
            { PC->ClientZoneTravelStatus(RuntimeError); continue; }
            Recovery.bPawnRestored = true;
        }
        if (Recovery.bReturnHandoff)
        {
            auto* Return = Returns.Find(Row.Key);
            if (!Return || Return->Player.Get() != PC) continue;
            Return->bRebinding = false;
            PendingRecovery.Remove(Row.Key); RestoreRequested.Remove(Row.Key);
            FinishedHandoffs.Add(Row.Key);
        }
        else AcknowledgeRecovery(Row.Key);
    }
    for (const FString& Id : FinishedHandoffs) Recoveries.Remove(Id);
    if (Encounter) Encounter->bRecoveringCharacters = !Recoveries.IsEmpty();
}
void UWarCampaignSiegeSubsystem::ApplyLease(const TSharedPtr<FJsonObject>& Lease)
{
    FString Owner, LeaseZone;
    if (!Lease || !Lease->TryGetStringField(TEXT("hostId"), Owner) || Owner != HostId
        || !Lease->TryGetStringField(TEXT("zoneId"), LeaseZone) || LeaseZone != TEXT("aegis_capital"))
    {
        bOwnerLeaseReady = false;
        if (Encounter) { Encounter->bLeasePaused = true; Encounter->Status = TEXT("This siege lease belongs to another native host or zone. Admission remains protected."); }
        return;
    }
    FString Activation, Revision; double Round = 0, Version = 0, Expires = 0, Seq = 0;
    if (!Lease || !Lease->TryGetStringField(TEXT("activationId"), Activation) || !Lease->TryGetStringField(TEXT("contentRevision"), Revision)
        || !Lease->TryGetNumberField(TEXT("rulesVersion"), Version) || Version != 2 || !Lease->TryGetNumberField(TEXT("round"), Round)
        || !Lease->TryGetNumberField(TEXT("sequence"), Seq) || !Lease->TryGetNumberField(TEXT("expiresAt"), Expires)) return;
    LeaseUntil = GetWorld()->GetTimeSeconds() + FMath::Max(0., Expires / 1000. - EpochSeconds() - .25);
    if (!Encounter) { LoadingActivation=Activation;LoadingRevision=Revision; }
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>(); FString ContentError;
    if (Streaming && !Encounter && LeaseUntil>GetWorld()->GetTimeSeconds())
    { Streaming->PinZone(this,TEXT("aegis_capital")); BootstrapLeaseUntil=LeaseUntil; }
    if (!Streaming || !Streaming->EnsureZone(TEXT("aegis_capital"), ContentError) || !Streaming->IsZoneReady(TEXT("aegis_capital"))) return;
    if (!Encounter)
    {
        AWarSiegeBattlefield* Battlefield = nullptr;
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld()); It; ++It) { if (Battlefield) return; Battlefield = *It; }
        if (!Battlefield || !Battlefield->CityDefinition || Battlefield->CityDefinition->Revision != Revision
            || Battlefield->DefinitionVersion != 2 || !Battlefield->Validate(ContentError, EWarSiegeScenario::FullSiege, true)) return;
        Encounter = GetWorld()->SpawnActor<AWarSiegeEncounter>(); if (Encounter) Encounter->Battlefield = Battlefield;
    }
    if (!Encounter) return;
    const bool NewActivation = Encounter->ActivationId != Activation;
    if (NewActivation) Encounter->BeginCampaignPreparation(Activation, Revision, int32(Round));
    if (NewActivation || bReconcile)
    {
        const TSharedPtr<FJsonObject>* Json = nullptr; FWarSiegeState Restored; FString Error;
        if (!Lease->TryGetObjectField(TEXT("snapshot"), Json) || !RestoreSnapshot(*Json, Restored, Error))
        { Encounter->bLeasePaused = true; Encounter->Status = TEXT("Recorded siege state is invalid. Recovery remains protected."); return; }
        Encounter->Siege = Restored; Encounter->bPreparing = Restored.Phase == EWarSiegePhase::Waiting;
        bFinishedSnapshot = Restored.Phase == EWarSiegePhase::Finished; Encounter->bCheckpointPending = false;
        double Prep = 180; (*Json)->TryGetNumberField(TEXT("preparationRemaining"), Prep);
        Encounter->PreparationUntil = GetWorld()->GetTimeSeconds() + FMath::Clamp(Prep,0.,180.); bReconcile = false;
        if (Encounter->Battlefield) Encounter->Battlefield->ApplyMilestones(Restored);
    }
    Sequence = int32(Seq); bool Paused = false; Lease->TryGetBoolField(TEXT("paused"), Paused); Encounter->bLeasePaused = Paused || Encounter->bContentBlocked;
    const TSharedPtr<FJsonObject>* Safe = nullptr;
    if (Lease->TryGetObjectField(TEXT("safeEvacuationZones"), Safe))
    {
        Encounter->SafeEvacuationZones.Reset();
        for (EWarRealm Realm : {EWarRealm::Aegis,EWarRealm::Riftbound})
        {
            const TArray<TSharedPtr<FJsonValue>>* Zones = nullptr;
            if ((*Safe)->TryGetArrayField(Realm == EWarRealm::Aegis ? TEXT("aegis") : TEXT("riftbound"), Zones))
                for (const auto& Zone : *Zones) Encounter->SafeEvacuationZones.FindOrAdd(Realm).Add(FName(*Zone->AsString()));
        }
    }
    const TSharedPtr<FJsonObject>* Documents = nullptr; const TArray<TSharedPtr<FJsonValue>>* Saved = nullptr;
    if (Lease->TryGetObjectField(TEXT("characterSnapshots"), Documents) && (*Documents)->TryGetArrayField(TEXT("characters"), Saved))
        for (const auto& Value : *Saved) if (const auto Document = Value->AsObject()) Characters.Add(Document->GetStringField(TEXT("id")), CloneCharacter(Document));
    const TArray<TSharedPtr<FJsonValue>>* Participants = nullptr;
    if (!Lease->TryGetArrayField(TEXT("participants"), Participants)) return;
    ApprovedIds.Reset(); ConnectedIds.Reset();
    for (const auto& Value : *Participants) if (const auto Row = Value->AsObject())
    { FString Id; bool Connected = true; if (!Row->TryGetStringField(TEXT("characterId"), Id)) continue; Row->TryGetBoolField(TEXT("connected"), Connected); ApprovedIds.Add(Id); if (Connected) ConnectedIds.Add(Id); }
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = Cast<AWarPlayerController>(It->Get()); auto* PS = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr; if (!PS) continue;
        bool Included = false;
        for (const auto& Value : *Participants)
        {
            const auto Row = Value->AsObject(); FString Id, Realm; bool Connected = true;
            if (!Row || !Row->TryGetStringField(TEXT("characterId"), Id) || !Row->TryGetStringField(TEXT("realm"), Realm)) continue;
            Row->TryGetBoolField(TEXT("connected"), Connected);
            if (Id == PC->ScenarioCharacterId && Realm == (PS->GetRealm() == EWarRealm::Aegis ? TEXT("aegis") : TEXT("riftbound")))
            { Included = Connected; break; }
        }
        if (!Included && Encounter->Owns(PS)) Encounter->Leave(PC);
        else if (Included && !PS->IsScenarioTransferPending() && !PendingRecovery.Contains(PC->ScenarioCharacterId)) { FString Error; Encounter->Enroll(PC, Error); }
    }
    bOwnerLeaseReady = true;
}
EWarCampaignLeaseRequest UWarCampaignSiegeSubsystem::LeaseRequestDue(bool Paused,double Now,double Until,double NextAttempt)
{
    if (!FMath::IsFinite(Now) || !FMath::IsFinite(Until) || !FMath::IsFinite(NextAttempt) || Now<NextAttempt)
        return EWarCampaignLeaseRequest::None;
    if (Paused || Now>=Until) return EWarCampaignLeaseRequest::Reactivate;
    return Until-Now<=5 ? EWarCampaignLeaseRequest::Heartbeat : EWarCampaignLeaseRequest::None;
}

void UWarCampaignSiegeSubsystem::Tick(float Delta)
{
    if (Url.IsEmpty() || GetWorld()->GetNetMode() == NM_Client || Cast<AWarSiegeGameMode>(GetWorld()->GetAuthGameMode())) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Encounter) { LoadingActivation.Reset();LoadingRevision.Reset(); }
    if (BootstrapLeaseUntil>0 && (Now>=BootstrapLeaseUntil || Encounter))
    {
        if (auto* Streaming=GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>()) Streaming->ReleaseZone(this);
        BootstrapLeaseUntil=0;
    }
    if (!WalError.IsEmpty())
    {
        if (Encounter) { Encounter->bLeasePaused = true; Encounter->Status = WalError; }
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (auto* PC = Cast<AWarPlayerController>(It->Get()))
                if (auto* PS = PC->GetPlayerState<AWarPlayerState>()) PS->SetScenarioTransferPending(true);
        return;
    }
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* PC = Cast<AWarPlayerController>(It->Get())) PrepareCharacter(PC);
    if (Now >= NextAdmissionAttempt) { NextAdmissionAttempt = Now + 1; FinishAdmissions(); }
    if (Encounter && !Encounter->ActivationId.IsEmpty() && Now >= LeaseUntil)
    { Encounter->bLeasePaused = true; bOwnerLeaseReady=false; bReconcile = true; Encounter->Status = TEXT("Campaign host connection interrupted. Siege is paused; your character is retained."); }
    if (bBusy) return;
    // Enrollment and recovery queues must not starve the owning-host lease.
    if (!Token.IsEmpty() && ((Encounter && !Encounter->ActivationId.IsEmpty()) || !LoadingActivation.IsEmpty()))
    {
        const auto Maintenance=LeaseRequestDue(Encounter ? Encounter->bLeasePaused : Now>=LeaseUntil,Now,LeaseUntil,NextLeaseAttempt);
        if (Maintenance!=EWarCampaignLeaseRequest::None)
        {
            NextLeaseAttempt=Now+2;NextHeartbeat=Now+5;
            const bool Reactivate=Maintenance==EWarCampaignLeaseRequest::Reactivate;
            auto Value=Body(!Reactivate);
            if (!Reactivate && !Encounter) Value->SetStringField(TEXT("activationId"),LoadingActivation);
            if (Reactivate)
            { Value->SetStringField(TEXT("contentRevision"),Encounter ? Encounter->ContentRevision : LoadingRevision);Value->SetNumberField(TEXT("rulesVersion"),2); }
            Request(Reactivate ? TEXT("activate") : TEXT("heartbeat"),Value,
                [this,Reactivate](bool Ok,TSharedPtr<FJsonObject> Lease,FString Error) {
                    if (Ok) { bReconcile|=Reactivate;ApplyLease(Lease); }
                    else if (Encounter) { bOwnerLeaseReady=false;Encounter->bLeasePaused=true;bReconcile=true;Encounter->Status=Error; }
                });
            return;
        }
        if (Encounter ? Encounter->bLeasePaused : Now>=LeaseUntil) return;
    }
    if (!Requests.IsEmpty() && Now < RetryAt) return;
    if (!Requests.IsEmpty()) { auto Row = MoveTemp(Requests[0]); Requests.RemoveAt(0); Request(Row.Path, Row.Value, MoveTemp(Row.Reply)); return; }
    if (!Token.IsEmpty() && !LocalWals.IsEmpty()) { if (Now >= RetryAt) ReplayWals(); return; }
    FinishRecoveries(); FinishReturns();
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It) if (auto* PC = Cast<AWarPlayerController>(It->Get())) Recover(PC);
    if (bBusy || Now < NextPoll) return; NextPoll = Now + 2;
    if (Token.IsEmpty())
    {
        Request(TEXT("register"), Body(), [this](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) {
            if (Ok) { Data->TryGetStringField(TEXT("token"), Token); ObserveRecovery(Data); bReconcile = true; }
            else UE_LOG(LogTemp, Warning, TEXT("WAR_CAMPAIGN_SIEGE_HOST unavailable: %s"), *Error);
        }); return;
    }
    if (Encounter && !Encounter->ActivationId.IsEmpty())
    {
        if (Now >= NextStatus)
        {
            NextStatus = Now+10;
            Request(TEXT("status"), Body(), [this](bool Ok,TSharedPtr<FJsonObject> Data,FString) {
                if (!Ok) return; ObserveRecovery(Data); const TSharedPtr<FJsonObject>* Lease = nullptr;
                if (Data->TryGetObjectField(TEXT("lease"), Lease)) ApplyLease(*Lease);
                else bOwnerLeaseReady = true;
            }); return;
        }
        if (Now >= NextHeartbeat)
        {
            NextHeartbeat = Now + 5;
            Request(TEXT("heartbeat"), Body(true), [this](bool Ok,TSharedPtr<FJsonObject> Lease,FString Error) { if (Ok) ApplyLease(Lease); else bReconcile = true; }); return;
        }
        if (Encounter->bLeasePaused)
        {
            auto Value = Body(); Value->SetStringField(TEXT("contentRevision"), Encounter->ContentRevision); Value->SetNumberField(TEXT("rulesVersion"), 2);
            Request(TEXT("activate"), Value, [this](bool Ok,TSharedPtr<FJsonObject> Lease,FString Error) { if (Ok) { bReconcile = true; ApplyLease(Lease); } }); return;
        }
        if (!Recoveries.IsEmpty()) return;
        if (bFinishedSnapshot)
        {
            auto Value = Body(true); Value->SetStringField(TEXT("reason"), Encounter->Siege.bAttackersWon ? TEXT("commander_defeated") : TEXT("stage_timeout"));
            Request(TEXT("finish"), Value, [this](bool Ok,TSharedPtr<FJsonObject> Lease,FString Error) {
                if (Ok && Encounter)
                {
                    FString Activation, Result, Owner;
                    const FString Expected=Encounter->Siege.bAttackersWon ? TEXT("city_captured") : TEXT("city_defended");
                    if (!Lease || !Lease->TryGetStringField(TEXT("activationId"),Activation) || Activation != Encounter->ActivationId
                        || !Lease->TryGetStringField(TEXT("hostId"),Owner) || Owner != HostId
                        || !Lease->TryGetStringField(TEXT("result"),Result) || Result != Expected)
                    { Encounter->bLeasePaused=true; Encounter->Status=TEXT("Campaign settlement acknowledgment does not match this encounter."); return; }
                    SettledActivation=Activation; SettledResult=Result;
                    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
                        if (auto* PC = Cast<AWarPlayerController>(It->Get()); PC && Encounter->Owns(PC->GetPlayerState<AWarPlayerState>()))
                        { PC->GetPlayerState<AWarPlayerState>()->SetScenarioTransferPending(true); Returns.Add(PC->ScenarioCharacterId, {PC, Encounter->ActivationId}); }
                    Encounter->CompleteCampaign(); Encounter->Destroy(); Encounter = nullptr; bFinishedSnapshot = false;
                    ApprovedIds.Reset(); ConnectedIds.Reset();
                }
                else if (Encounter) Encounter->Status = Error;
            }); return;
        }
        auto Value = Body(true); Value->SetNumberField(TEXT("sequence"), Sequence + 1);
        Value->SetObjectField(TEXT("snapshot"), Snapshot(Encounter->Siege, Encounter->bPreparing, Encounter->PreparationUntil - Now));
        const auto Documents = CaptureMembers();
        if (Documents.Num() != ConnectedIds.Num()) { Encounter->bCheckpointPending = true; Encounter->Status = TEXT("Siege checkpoint is waiting for every enrolled character document."); return; }
        Value->SetArrayField(TEXT("characters"), Documents); const bool Finished = Encounter->Siege.Phase == EWarSiegePhase::Finished;
        Request(TEXT("update"), Value, [this,Finished](bool Ok,TSharedPtr<FJsonObject> Lease,FString Error) {
            if (Ok) { ApplyLease(Lease); bFinishedSnapshot = Finished; if (Encounter) Encounter->bCheckpointPending = false; }
            else if (Encounter) { Encounter->bLeasePaused = true; bReconcile = true; Encounter->Status = Error; }
        }); return;
    }
    Request(TEXT("status"), Body(), [this](bool Ok,TSharedPtr<FJsonObject> Status,FString Error) {
        if (!Ok) return; ObserveRecovery(Status);
        const TSharedPtr<FJsonObject>* Lease = nullptr;
        if (Status->TryGetObjectField(TEXT("lease"), Lease)) { ApplyLease(*Lease); return; }
        bOwnerLeaseReady = true;
        bool Eligible = false;
        if (!Status->TryGetBoolField(TEXT("eligible"), Eligible) || !Eligible)
        {
            if (auto* Streaming=GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>()) Streaming->ReleaseZone(this);
            BootstrapLeaseUntil=0;LoadingActivation.Reset();LoadingRevision.Reset();return;
        }
        auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
        if (Streaming) { Streaming->PinZone(this,TEXT("aegis_capital"));BootstrapLeaseUntil=GetWorld()->GetTimeSeconds()+15; }
        if (!Streaming || !Streaming->EnsureZone(TEXT("aegis_capital"), Error) || !Streaming->IsZoneReady(TEXT("aegis_capital"))) return;
        AWarSiegeBattlefield* Battlefield = nullptr;
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld()); It; ++It) { if (Battlefield) return; Battlefield = *It; }
        if (!Battlefield || !Battlefield->CityDefinition || Battlefield->DefinitionVersion != 2 || !Battlefield->Validate(Error, EWarSiegeScenario::FullSiege, true)) return;
        auto Value = Body(); Value->SetStringField(TEXT("contentRevision"), Battlefield->CityDefinition->Revision); Value->SetNumberField(TEXT("rulesVersion"), 2);
        Request(TEXT("activate"), Value, [this](bool Accepted,TSharedPtr<FJsonObject> Activated,FString Reason) { if (Accepted) ApplyLease(Activated); });
    });
}
void UWarCampaignSiegeSubsystem::Enroll(AWarPlayerController* Player, bool Join)
{
    auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    auto* Pawn = Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    if (!PS || !PrepareCharacter(Player) || PS->GetRealm() == EWarRealm::None || PS->IsScenarioTransferPending() || !Player->bCampaignIdentityProvisioned || Player->ScenarioCharacterId.IsEmpty()
        || (Join && (!Pawn || Pawn->IsDead() || !Pawn->IsVisualReady()))
        || (PS->IsSiegeMember() && PS->GetSiegeEncounter() != Encounter) || !Player->HasAuthority() || !Encounter || Encounter->ActivationId.IsEmpty() || Token.IsEmpty())
    { if (Player) Player->ClientZoneTravelStatus(TEXT("Campaign enrollment needs your provisioned, living character and a ready siege. Connect your character and retry.")); return; }
    auto Character = Capture(Player); if (!Character) { Player->ClientZoneTravelStatus(TEXT("Your campaign document is awaiting recovery.")); return; }
    auto Value = Body(true); Value->SetStringField(TEXT("characterId"), Player->ScenarioCharacterId);
    Value->SetStringField(TEXT("realm"), PS->GetRealm() == EWarRealm::Aegis ? TEXT("aegis") : TEXT("riftbound"));
    Value->SetStringField(TEXT("action"), Join ? TEXT("join") : TEXT("leave")); Value->SetObjectField(TEXT("character"), Character);
    const FString Id = Player->ScenarioCharacterId; MembershipPending.Add(Id); PS->SetScenarioTransferPending(true);
    const TWeakObjectPtr<AWarPlayerController> Weak = Player;
    Request(TEXT("membership"), Value, [this,Weak,Join,Id,Membership=Value](bool Ok,TSharedPtr<FJsonObject> Lease,FString Error) {
        MembershipPending.Remove(Id);
        auto* PC = Weak.Get();
        if (!PC) { if (Ok && Join) ReserveDisconnectedSeat(Membership); return; }
        if (!Encounter) { if (Ok) PendingRecovery.Add(Id); else if (auto* State = PC->GetPlayerState<AWarPlayerState>()) State->SetScenarioTransferPending(false); return; }
        if (Ok)
        {
            const FString Activation = Encounter->ActivationId;
            ApplyLease(Lease);
            if (Join)
            {
                Ok = Encounter->Enroll(PC, Error);
                if (!Ok) PendingRecovery.Add(Id);
                else if (!Encounter->bPreparing && PC->GetPlayerState<AWarPlayerState>()->GetCurrentZone() == TEXT("aegis_capital"))
                { PendingAdmissions.Add(Id, PC); FinishAdmissions(); }
            }
            else { Encounter->Leave(PC); Returns.Add(PC->ScenarioCharacterId, {PC, Activation}); }
        }
        if (Join || !Ok) if (auto* State = PC->GetPlayerState<AWarPlayerState>(); State && !PendingRecovery.Contains(Id) && !PendingAdmissions.Contains(Id)) State->SetScenarioTransferPending(false);
        PC->ClientZoneTravelStatus(PendingAdmissions.Contains(Id) ? TEXT("Your siege seat is reserved. Waiting for safe capital entry staging.")
            : Ok ? Join ? TEXT("Enrolled in the live siege. Enter through the capital portal; your normal stats apply.") : TEXT("Siege participation ended.") : Error);
    });
}
void UWarCampaignSiegeSubsystem::Disconnect(AWarPlayerController* Player)
{
    if (!Player || !Encounter || !Encounter->Owns(Player->GetPlayerState<AWarPlayerState>()) || Token.IsEmpty()) return;
    Checkpoint(Player); auto Value = Body(true); Value->SetStringField(TEXT("characterId"), Player->ScenarioCharacterId);
    const auto* PS = Player->GetPlayerState<AWarPlayerState>();
    Value->SetStringField(TEXT("realm"), PS->GetRealm() == EWarRealm::Aegis ? TEXT("aegis") : TEXT("riftbound")); Value->SetStringField(TEXT("action"), TEXT("disconnect"));
    PendingRecovery.Add(Player->ScenarioCharacterId);
    // Logout never creates a replacement pawn for a controller being destroyed.
    if (auto* State = Player->GetPlayerState<AWarPlayerState>()) State->SetSiegeMembership(nullptr);
    Request(TEXT("membership"), Value, [this](bool Ok,TSharedPtr<FJsonObject> Lease,FString) { if (Ok) ApplyLease(Lease); });
}
void UWarCampaignSiegeSubsystem::AcknowledgeRecovery(const FString& Id)
{
    auto* Recovery = Recoveries.Find(Id);
    if (!Recovery || Recovery->bAcknowledging || !Recovery->bPawnRestored || Recovery->Activation.IsEmpty()) return;
    auto Value = Body(); Value->SetStringField(TEXT("characterId"), Id); Value->SetNumberField(TEXT("revision"), Recovery->Revision);
    Recovery->bAcknowledging = true;
    Request(TEXT("restored"), Value, [this,Id](bool Ok,TSharedPtr<FJsonObject> Ack,FString Error) {
        auto* Entry = Recoveries.Find(Id); if (!Entry) return;
        if (!Ok || !ReturnedCharacterAck(Ack, Id, Entry->Revision, Entry->WalSequence, true, Error))
        { Entry->bAcknowledging = false; if (auto* PC = Entry->Player.Get()) PC->ClientZoneTravelStatus(Error); return; }
        auto* Recovered = Entry->Player.Get();
        // Restore acknowledges the old document. Release needs a second full checkpoint
        // containing the actual relocation/respawn, under its original journal custody.
        const bool ActiveMember = !Entry->bEvacuation && Encounter && Encounter->ActivationId == Entry->Activation && ApprovedIds.Contains(Id);
        if (!ActiveMember) Returns.Add(Id, {Entry->Player, Entry->Activation, Entry->bEvacuation});
        if (!Recovered)
        {
            // Logout can race the ACK. A later same-ID controller must request the
            // actual durable document again, even if this ACK cleared Node's flag.
            PendingRecovery.Add(Id); RestoreRequested.Remove(Id); Recoveries.Remove(Id); bReconcile = true;
            return;
        }
        PendingRecovery.Remove(Id); RestoreRequested.Remove(Id); Recoveries.Remove(Id); bReconcile = true;
        if (!ActiveMember)
        {
            // Keep the actual post-restoration document if this controller disappears
            // before its full return commits. A replacement cannot capture defaults.
            Returns.FindChecked(Id).Document = CloneCharacter(Capture(Recovered));
            if (auto* PS = Recovered->GetPlayerState<AWarPlayerState>()) PS->SetScenarioTransferPending(true);
            Recovered->ClientZoneTravelStatus(TEXT("Your character is restored. Saving its actual return before releasing recovery."));
        }
        else
        {
            if (auto* PS = Recovered->GetPlayerState<AWarPlayerState>()) PS->SetScenarioTransferPending(false);
            Recovered->ClientZoneTravelStatus(TEXT("Your recorded campaign character has been restored."));
            if (Encounter->Siege.Phase != EWarSiegePhase::Finished) Enroll(Recovered, true);
        }
    });
}

void UWarCampaignSiegeSubsystem::ReserveDisconnectedSeat(const TSharedPtr<FJsonObject>& AcceptedMembership)
{
    FString Id, Realm, Activation;
    if (!AcceptedMembership || !AcceptedMembership->TryGetStringField(TEXT("characterId"), Id)
        || !AcceptedMembership->TryGetStringField(TEXT("realm"), Realm)
        || !AcceptedMembership->TryGetStringField(TEXT("activationId"), Activation)) return;
    PendingRecovery.Add(Id);
    auto Value = Body(); Value->SetStringField(TEXT("activationId"), Activation);
    Value->SetStringField(TEXT("characterId"), Id); Value->SetStringField(TEXT("realm"), Realm);
    Value->SetStringField(TEXT("action"), TEXT("disconnect"));
    // The acknowledged baseline owns this seat even when its original controller is gone.
    Request(TEXT("membership"), Value, [this](bool Ok,TSharedPtr<FJsonObject> Lease,FString) { if (Ok) ApplyLease(Lease); });
}

bool UWarCampaignSiegeSubsystem::StagesRecoveryAtEntry(const FString& Id, const TSharedPtr<FJsonObject>& Character) const
{
    const TSharedPtr<FJsonObject>* Document = nullptr; FString Zone;
    return Encounter && ApprovedIds.Contains(Id) && Character && Character->TryGetObjectField(TEXT("document"), Document)
        && (*Document)->TryGetStringField(TEXT("zone"), Zone) && Zone == TEXT("aegis_capital");
}
void UWarCampaignSiegeSubsystem::Checkpoint(AWarPlayerController* Player, bool Evacuation)
{
    if (!Player || LocalWals.Contains(Player->ScenarioCharacterId) || !Encounter || Encounter->ActivationId.IsEmpty() || Token.IsEmpty() || CheckpointQueued.Contains(Player->ScenarioCharacterId)) return;
    // A new evacuation scope cannot precede the durable acknowledgment of the old return.
    if (Evacuation && IsCharacterReturnPending(Player)) return;
    auto Character = Capture(Player); if (!Character) return;
    const FString Id = Player->ScenarioCharacterId; CheckpointQueued.Add(Id);
    if (Evacuation) if (auto* PS = Player->GetPlayerState<AWarPlayerState>()) PS->SetScenarioTransferPending(true);
    auto Value = Body(true); Value->SetObjectField(TEXT("character"), Character); Value->SetStringField(TEXT("scope"), Evacuation ? TEXT("evacuation") : TEXT("participant"));
    const TWeakObjectPtr<AWarPlayerController> Weak = Player;
    Request(TEXT("checkpoint"), Value, [this,Id,Evacuation,Weak](bool Ok,TSharedPtr<FJsonObject>,FString Error) {
        CheckpointQueued.Remove(Id); if (Ok && Evacuation) EvacuationReady.Add(Id);
        if (!Ok && Evacuation) if (auto* PC = Weak.Get()) if (auto* PS = PC->GetPlayerState<AWarPlayerState>(); PS && !PendingRecovery.Contains(Id)) PS->SetScenarioTransferPending(false);
        if (!Ok && Encounter) Encounter->Status = Error;
    });
}
bool UWarCampaignSiegeSubsystem::HasEvacuationCheckpoint(const AWarPlayerController* Player) const
{ return Player && !Player->ScenarioCharacterId.IsEmpty() && EvacuationReady.Contains(Player->ScenarioCharacterId); }
void UWarCampaignSiegeSubsystem::Evacuated(AWarPlayerController* Player)
{
    if (!Player || !EvacuationReady.Remove(Player->ScenarioCharacterId)) return;
    Returns.Add(Player->ScenarioCharacterId, {Player, Encounter ? Encounter->ActivationId : FString(), true});
    if (auto* PS = Player->GetPlayerState<AWarPlayerState>()) PS->SetScenarioTransferPending(true);
}
void UWarCampaignSiegeSubsystem::FinishReturns()
{
    for (auto& Row : Returns)
    {
        auto& Return = Row.Value; auto* PC = Return.Player.Get();
        const auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
        if (!Pawn || Pawn->IsDead() || !Pawn->IsVisualReady() || Return.bSending || Return.Activation.IsEmpty() || LocalWals.Contains(Row.Key)) continue;
        const auto* PS = PC->GetPlayerState<AWarPlayerState>();
        const auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
        if (!PS || !Streaming || !Streaming->IsZoneReady(PS->GetCurrentZone(), PC)) continue;
        SendReturnCheckpoint(Row.Key);
    }
}
void UWarCampaignSiegeSubsystem::SendReturnCheckpoint(const FString& Id)
{
    auto* Return = Returns.Find(Id); const auto* PreviousAck = CharacterAcks.Find(Id);
    if (!Return || Return->bSending || Return->Activation.IsEmpty() || !PreviousAck || PreviousAck->Revision == MAX_int32 || LocalWals.Contains(Id)) return;
    auto* PC = Return->Player.Get();
    auto Character = Return->bRebinding ? CloneCharacter(Return->Document) : Capture(PC); if (!Character) return;
    Return->Document = CloneCharacter(Character);
    auto Value = Body(); Value->SetStringField(TEXT("activationId"), Return->Activation);
    Value->SetObjectField(TEXT("character"), Character); Value->SetStringField(TEXT("scope"), Return->bEvacuation ? TEXT("evacuation") : TEXT("participant"));
    Value->SetBoolField(TEXT("returned"), true); Return->bSending = true;
    const int32 MinimumRevision = PreviousAck->Revision + (Return->bCommitted ? 0 : 1), WalSequence = PreviousAck->WalSequence;
    Request(TEXT("checkpoint"), Value, [this,Id,MinimumRevision,WalSequence](bool Ok,TSharedPtr<FJsonObject> Ack,FString Error) {
        auto* Entry = Returns.Find(Id); if (!Entry) return;
        if (!Ok || !ReturnedCharacterAck(Ack, Id, MinimumRevision, WalSequence, false, Error))
        { Entry->bSending = false; if (auto* Player = Entry->Player.Get()) Player->ClientZoneTravelStatus(Error); return; }
        if (Entry->bRebinding)
        { Entry->bCommitted = true; Entry->bSending = false; return; }
        if (auto* Player = Entry->Player.Get()) if (auto* PS = Player->GetPlayerState<AWarPlayerState>(); PS && !PendingRecovery.Contains(Id)) PS->SetScenarioTransferPending(false);
        Returns.Remove(Id);
    });
}
void UWarCampaignSiegeSubsystem::RestoreReturnHandoff(AWarPlayerController* Player)
{
    const FString Id = Player ? Player->ScenarioCharacterId : FString();
    auto* Return = Returns.Find(Id);
    if (!Return || !Return->bRebinding || Return->bSending || !Return->Document || Recoveries.Contains(Id)) return;
    auto* PS = Player->GetPlayerState<AWarPlayerState>(); if (!PS) return;
    FString Error;
    // This is the complete immutable document captured by the departed native pawn,
    // never a new controller's defaults or a forbidden restore of a returned journal.
    if (!Player->GetGameInstance()) return;
    if (APawn* Pawn = Player->GetPawn()) { Player->UnPossess(); Pawn->Destroy(); }
    if (!WarScenarioTransport::Restore(Player, Return->Document, false, Error))
    { Player->ClientZoneTravelStatus(Error); return; }
    FRecovery Recovery; Recovery.Player = Player; Recovery.Character = CloneCharacter(Return->Document);
    Recovery.Activation = Return->Activation; Recovery.bEvacuation = Return->bEvacuation;
    Recovery.bSafeRelocation = true; Recovery.bReturnHandoff = true;
    const auto Runtime = Recovery.Character->GetObjectField(TEXT("document"))->GetObjectField(TEXT("runtime"));
    Runtime->TryGetBoolField(TEXT("dead"), Recovery.bRespawnPending);
    Recoveries.Add(Id, MoveTemp(Recovery)); PendingRecovery.Add(Id); RestoreRequested.Add(Id);
    PS->SetScenarioTransferPending(true);
    if (auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>()) Mode->RestartPlayer(Player);
}

void UWarCampaignSiegeSubsystem::ObserveAcks(const TSharedPtr<FJsonObject>& Data)
{
    if (!Data) return;
    const auto Read = [this](const TSharedPtr<FJsonObject>& Row) {
        FString Id; double Revision = 0, WalSequence = 0; bool Pending = false;
        if (!Row || !Row->TryGetStringField(TEXT("characterId"),Id) || !Row->TryGetNumberField(TEXT("revision"),Revision)
            || Revision < 1 || Revision > MAX_int32 || FMath::FloorToDouble(Revision) != Revision) return;
        Row->TryGetNumberField(TEXT("walSequence"),WalSequence);
        if (WalSequence < 0 || WalSequence > MAX_int32 || FMath::FloorToDouble(WalSequence) != WalSequence) return;
        auto& Ack = CharacterAcks.FindOrAdd(Id);
        if (Revision >= Ack.Revision) Ack = {int32(Revision),int32(WalSequence)};
        if (Row->TryGetBoolField(TEXT("recoveryPending"),Pending) && Pending) PendingRecovery.Add(Id);
    };
    Read(Data);
    for (const TCHAR* Key : {TEXT("characterAcks"),TEXT("characterRecovery")})
    {
        const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
        if (Data->TryGetArrayField(Key,Rows)) for (const auto& Value : *Rows) Read(Value->AsObject());
    }
}
bool UWarCampaignSiegeSubsystem::JournalsMutations(const AWarPlayerState* Player) const
{
    const auto* Siege = Player ? Player->GetSiegeEncounter() : nullptr;
    return !Url.IsEmpty() && Player && Player->HasAuthority() && !Player->IsScenarioTransferPending()
        && Siege && Siege->bCampaign && !Siege->ActivationId.IsEmpty() && Player->GetSiegeUnit() == EWarSiegeUnit::Participant;
}
bool UWarCampaignSiegeSubsystem::CommitMutation(AWarPlayerController* Player, FString& Error)
{
    const FString Id = Player ? Player->ScenarioCharacterId : FString();
    auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    const auto* Siege = PS ? PS->GetSiegeEncounter() : nullptr;
    const auto* Ack = CharacterAcks.Find(Id);
    if (!Player || !JournalsMutations(PS) || Id.IsEmpty() || !Ack || Ack->Revision < 1 || Ack->Revision == MAX_int32
        || Ack->WalSequence == MAX_int32 || bBusy || !Requests.IsEmpty() || CheckpointQueued.Contains(Id)
        || LocalWals.Contains(Id) || PendingRecovery.Contains(Id) || !WalError.IsEmpty() || Token.IsEmpty())
    { Error = TEXT("Your campaign character checkpoint is in flight. Retry this mutation after it is acknowledged."); return false; }
    auto Character = Capture(Player);
    if (!Character) { Error = TEXT("Cannot save the complete campaign character mutation. Recovery stays protected."); return false; }
    FString CharacterText; FJsonSerializer::Serialize(Character,TJsonWriterFactory<>::Create(&CharacterText));
    const FTCHARToUTF8 CharacterBytes(*CharacterText);
    if (CharacterBytes.Length() > 258048)
    { Error = TEXT("The complete character document exceeds the trusted journal limit. This mutation was rolled back."); return false; }
    auto Value = Body(); Value->SetStringField(TEXT("activationId"),Siege->ActivationId);
    Value->SetStringField(TEXT("characterId"),Id); Value->SetNumberField(TEXT("baseRevision"),Ack->Revision);
    Value->SetNumberField(TEXT("walSequence"),Ack->WalSequence+1); Value->SetObjectField(TEXT("character"),Character);
    auto Record = MakeShared<FJsonObject>(); Record->SetNumberField(TEXT("schemaVersion"),1);
    Record->SetStringField(TEXT("hostId"),HostId); Record->SetObjectField(TEXT("body"),Value);
    IFileManager::Get().MakeDirectory(*WalDirectory,true);
    const FString Filename = WalDirectory/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));
    if (!FlushMutationWal(Filename,Record,Error)) return false;
    LocalWals.Add(Id,{Filename,Value,Player});
    PS->SetScenarioTransferPending(true);
    if (Encounter) { Encounter->bCheckpointPending = true; Encounter->Status = TEXT("Saving a committed character mutation before siege progress continues."); }
    return true;
}
void UWarCampaignSiegeSubsystem::ReplayWals()
{
    for (auto& Row : LocalWals)
    {
        const FString Id = Row.Key; auto& Wal = Row.Value;
        if (Wal.bSending) continue;
        if (!Wal.Player.IsValid()) for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (auto* PC = Cast<AWarPlayerController>(It->Get()); PC && PC->ScenarioCharacterId == Id) { Wal.Player = PC; break; }
        if (auto* PC = Wal.Player.Get()) if (auto* PS = PC->GetPlayerState<AWarPlayerState>()) PS->SetScenarioTransferPending(true);
        Wal.bSending = true;
        Request(TEXT("replay"),Wal.Body,[this,Id](bool Ok,TSharedPtr<FJsonObject> Ack,FString Error) {
            auto* Wal = LocalWals.Find(Id); if (!Wal) return;
            if (!Ok)
            { Wal->bSending = false; RetryAt = GetWorld()->GetTimeSeconds()+2; if (Encounter) { Encounter->bLeasePaused = true; Encounter->Status = Error; } return; }
            FString AckId; double Version = 0, Revision = 0, SequenceNumber = 0; bool Pending = true;
            if (!Ack || !Ack->TryGetNumberField(TEXT("version"),Version) || Version != 1
                || !Ack->TryGetStringField(TEXT("characterId"),AckId) || AckId != Id
                || !Ack->TryGetNumberField(TEXT("revision"),Revision) || Revision < Wal->Body->GetNumberField(TEXT("baseRevision"))+1
                || Revision > MAX_int32 || FMath::FloorToDouble(Revision) != Revision
                || !Ack->TryGetNumberField(TEXT("walSequence"),SequenceNumber) || SequenceNumber != Wal->Body->GetNumberField(TEXT("walSequence"))
                || !Ack->TryGetBoolField(TEXT("recoveryPending"),Pending))
            { Wal->bSending = false; WalError = TEXT("Character WAL acknowledgment is invalid; keep the private record for protected recovery."); return; }
            // Removing an acknowledged file is retryable; a restart replays the exact sequence idempotently.
            if (!IFileManager::Get().Delete(*Wal->Filename,false,true)) { Wal->bSending = false; return; }
            if (auto* PC = Wal->Player.Get()) if (auto* PS = PC->GetPlayerState<AWarPlayerState>(); PS && !Pending) PS->SetScenarioTransferPending(false);
            if (Pending) PendingRecovery.Add(Id);
            LocalWals.Remove(Id); bReconcile = true;
            if (Encounter && LocalWals.IsEmpty()) Encounter->bCheckpointPending = false;
        });
        return;
    }
}
bool UWarCampaignSiegeSubsystem::FlushMutationWal(const FString& Filename,const TSharedPtr<FJsonObject>& Record,FString& Error)
{
    FString Text; if (!Record || IFileManager::Get().FileExists(*Filename) || !FJsonSerializer::Serialize(Record,TJsonWriterFactory<>::Create(&Text)))
    { Error = TEXT("Cannot overwrite an existing character mutation WAL."); return false; }
    const FTCHARToUTF8 Bytes(*Text);
    TUniquePtr<IFileHandle> File(FPlatformFileManager::Get().GetPlatformFile().OpenWrite(*Filename));
    if (!File || !File->Write(reinterpret_cast<const uint8*>(Bytes.Get()),Bytes.Length()) || !File->Flush(true))
    { File.Reset(); IFileManager::Get().Delete(*Filename); Error = TEXT("The private character WAL could not be flushed. The mutation was rolled back."); return false; }
    return true;
}
bool UWarCampaignSiegeSubsystem::PrepareCharacter(AWarPlayerController* Player)
{
    if (Url.IsEmpty()) return true;
    auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr; if (!PS) return false;
    if (!Player->bCampaignIdentityProvisioned && !ProvisionedCharacterId.IsEmpty() && GetWorld()->GetNumPlayerControllers() == 1
        && (Player->ScenarioCharacterId.IsEmpty() || Player->ScenarioCharacterId == ProvisionedCharacterId))
    { Player->ScenarioCharacterId = ProvisionedCharacterId; Player->bCampaignIdentityProvisioned = true; }
    if (!Player->bCampaignIdentityProvisioned || !StableCharacterId(Player->ScenarioCharacterId) || !WalError.IsEmpty())
    { PS->SetScenarioTransferPending(true); Player->ClientZoneTravelStatus(TEXT("This native campaign host requires an explicitly provisioned stable character ID before admission or recovery.")); return false; }
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (It->Get() != Player) if (const auto* Other = Cast<AWarPlayerController>(It->Get()); Other && Other->ScenarioCharacterId == Player->ScenarioCharacterId)
        { PS->SetScenarioTransferPending(true); return false; }
    const FString Id = Player->ScenarioCharacterId;
    if (Token.IsEmpty()) { IdentityHolds.Add(Id); PS->SetScenarioTransferPending(true); return false; }
    if (auto* Return = Returns.Find(Id))
    {
        PS->SetScenarioTransferPending(true);
        if (Return->Player.Get() != Player) { Return->Player = Player; Return->bRebinding = true; }
        if (Return->bRebinding)
        {
            if (Return->Document) RestoreReturnHandoff(Player);
            else PendingRecovery.Add(Id);
            const auto* Recovery = Recoveries.Find(Id);
            FString RecordedId;
            // RestartPlayer may construct the avatar only after this same controller
            // has received its trusted document. Possession reapplies the held movement.
            return Recovery && Recovery->Player.Get() == Player && Recovery->Activation == Return->Activation
                && Recovery->bEvacuation == Return->bEvacuation && Recovery->Character
                && Recovery->Character->TryGetStringField(TEXT("id"), RecordedId) && RecordedId == Id
                && !LocalWals.Contains(Id);
        }
        return true;
    }
    if (PendingRecovery.Contains(Id) || LocalWals.Contains(Id))
    { PS->SetScenarioTransferPending(true); return Recoveries.Contains(Id) && !LocalWals.Contains(Id); }
    if (IdentityHolds.Remove(Id) && !MembershipPending.Contains(Id) && !Returns.Contains(Id) && !Recoveries.Contains(Id)) PS->SetScenarioTransferPending(false);
    return true;
}
bool UWarCampaignSiegeSubsystem::SettlementAcknowledged(const FString& Activation,bool AttackersWon) const
{ return !Activation.IsEmpty() && Activation==SettledActivation && SettledResult==(AttackersWon ? TEXT("city_captured") : TEXT("city_defended")); }

bool UWarCampaignSiegeSubsystem::IsEnrollmentPending(const AWarPlayerController* Player) const
{ return Player && (MembershipPending.Contains(Player->ScenarioCharacterId) || PendingAdmissions.Contains(Player->ScenarioCharacterId)); }
bool UWarCampaignSiegeSubsystem::IsCharacterReturnPending(const AWarPlayerController* Player) const
{ return Player && Returns.Contains(Player->ScenarioCharacterId); }

bool UWarCampaignSiegeSubsystem::HasPendingCapitalEnrollment() const
{
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (const auto* Player = Cast<AWarPlayerController>(It->Get()); IsEnrollmentPending(Player))
            if (const auto* PS = Player->GetPlayerState<AWarPlayerState>(); PS && PS->GetCurrentZone() == TEXT("aegis_capital")) return true;
    return false;
}

void UWarCampaignSiegeSubsystem::FinishAdmissions()
{
    TArray<FString> Finished;
    for (const auto& Row : PendingAdmissions)
    {
        auto* Player = Row.Value.Get(); auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        if (!PS) { Finished.Add(Row.Key); continue; }
        PS->SetScenarioTransferPending(true);
        if (!Encounter || !Encounter->Owns(PS))
        { if (!Returns.Contains(Row.Key)) PendingRecovery.Add(Row.Key); Finished.Add(Row.Key); continue; }
        if (Encounter->Siege.Phase == EWarSiegePhase::Finished) continue;
        // Remote seats retain their ordinary location. Only a capital arrival crosses this barrier.
        FString Error;
        if (!Encounter->bPreparing && PS->GetCurrentZone() == TEXT("aegis_capital") && !Encounter->StageCampaignParticipant(Player, Error))
        { Player->ClientZoneTravelStatus(Error); continue; }
        if (!PendingRecovery.Contains(Row.Key) && !Returns.Contains(Row.Key)) PS->SetScenarioTransferPending(false);
        Finished.Add(Row.Key);
    }
    for (const auto& Id : Finished) PendingAdmissions.Remove(Id);
}
