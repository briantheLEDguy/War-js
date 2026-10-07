#include "WarCitadelSiegeProof.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeNavigation.h"
#include "WarSiegeBattlefield.h"
#include "WarSiegeEquipment.h"
#include "WarSiegeEscort.h"
#include "WarCityDefinition.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "WarAbilityRuntime.h"
#include "WarAbilityCatalog.h"
#include "WarCombatStatus.h"
#include "WarCampaignCombatState.h"
#include "WarCampaignCombatDefinition.h"
#include "WarCharacterVisualDefinition.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarScenarioTransport.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarZoneAnchor.h"
#include "JsonObjectConverter.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformMemory.h"
#include "HAL/PlatformTime.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/EngineVersion.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/SecureHash.h"
#include "Modules/ModuleManager.h"
#include "IPlatformCrypto.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/WorldSettings.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "ContentStreaming.h"
#include "UnrealClient.h"
#include "DynamicRHI.h"
#include "RHIStats.h"
#include "RenderTimer.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Serialization/JsonSerializer.h"

bool WarCitadelProofTactics::CanTarget(const AWarSiegeEncounter* Encounter, const AWarCharacter* Source,
    const AWarCharacter* Target, float Range)
{
    return Encounter && Source && Target && Encounter->Owns(Target->GetPlayerState<AWarPlayerState>())
        && Source->CanAbilityTarget(Target, Range);
}

namespace WarCitadelProofHash
{
    bool Bytes(const uint8* Data, int64 Length, FString& OutHash, FString& Error)
    {
        OutHash.Reset(); Error.Reset();
        if (Length < 0 || Length > MAX_int32 || (Length > 0 && !Data))
        { Error = TEXT("SHA-256 input is missing or exceeds the bounded native buffer."); return false; }
        auto* Provider = FModuleManager::LoadModulePtr<IPlatformCrypto>(TEXT("PlatformCrypto"));
        if (!Provider) { Error = TEXT("The engine SHA-256 provider is unavailable."); return false; }
        auto Context = Provider->CreateContext(); TArray<uint8> Digest;
        if (!Context || !Context->CalcSHA256(MakeArrayView(Data, int32(Length)), Digest) || Digest.Num() != 32)
        { Error = TEXT("The engine SHA-256 provider could not compute the receipt hash."); return false; }
        OutHash = BytesToHex(Digest.GetData(), Digest.Num()).ToLower(); return true;
    }
    bool Text(const FString& Value, FString& OutHash, FString& Error)
    {
        const FTCHARToUTF8 Utf8(*Value);
        return Bytes(reinterpret_cast<const uint8*>(Utf8.Get()), Utf8.Length(), OutHash, Error);
    }
    bool File(const FString& Filename, FString& OutHash, FString& Error)
    {
        OutHash.Reset(); Error.Reset();
        const int64 Size = IFileManager::Get().FileSize(*Filename); TArray<uint8> Payload;
        if (Size < 0 || Size > MAX_int32 - 2 || !FFileHelper::LoadFileToArray(Payload, *Filename, FILEREAD_Silent))
        { Error = TEXT("The SHA-256 receipt file is unavailable or exceeds the bounded native reader."); return false; }
        return Bytes(Payload.GetData(), Payload.Num(), OutHash, Error);
    }
}

namespace
{
    constexpr const TCHAR* PreservedCity=TEXT("/Game/Cities/Shared/aegis_capital/City");
    constexpr const TCHAR* PreservedRevision=TEXT("6ffd751f94efa5aa261779a6853262a6ca5128376c7a65a369e69943de9f6a2f");
    constexpr const TCHAR* BaselineFixtureMode=TEXT("earned_progression");
    FString SiegePhase(EWarSiegePhase Phase)
    { return Phase==EWarSiegePhase::Active ? TEXT("active") : Phase==EWarSiegePhase::Transition ? TEXT("transition")
        : Phase==EWarSiegePhase::Finished ? TEXT("finished") : TEXT("waiting"); }
    void SiegeClock(const FWarSiegeState& State,const TSharedPtr<FJsonObject>& Row)
    {
        Row->SetNumberField(TEXT("mainClaims"),State.MainClaims);Row->SetNumberField(TEXT("optionalClaims"),State.OptionalClaims);
        Row->SetNumberField(TEXT("siegeElapsedSeconds"),State.Elapsed);
        Row->SetNumberField(TEXT("stageRemainingSeconds"),State.Phase==EWarSiegePhase::Active && !State.bOvertime ? State.Remaining : 0);
        Row->SetNumberField(TEXT("transitionRemainingSeconds"),State.Phase==EWarSiegePhase::Transition ? State.Remaining : 0);
        Row->SetNumberField(TEXT("overtimeRemainingSeconds"),State.Phase==EWarSiegePhase::Active && State.bOvertime ? State.Remaining : 0);
        TArray<TSharedPtr<FJsonValue>> Milestones;
        for (double Time:State.MilestoneSeconds) Milestones.Add(MakeShared<FJsonValueNumber>(Time));
        Row->SetArrayField(TEXT("milestoneSeconds"),Milestones);
    }
    bool Hex(const FString& Value, int32 Length)
    { if (Value.Len() != Length) return false; for (TCHAR C : Value) if (!FChar::IsHexDigit(C)) return false; return true; }
    FString FileHash(const FString& File)
    {
        FString Digest, Error;
        return WarCitadelProofHash::File(File, Digest, Error) ? Digest : FString();
    }
    FString TextHash(const FString& Text)
    {
        FString Digest, Error;
        return WarCitadelProofHash::Text(Text, Digest, Error) ? Digest : FString();
    }
    TArray<TSharedPtr<FJsonValue>> JsonPoint(const FVector& Point)
    { return {MakeShared<FJsonValueNumber>(Point.X),MakeShared<FJsonValueNumber>(Point.Y),MakeShared<FJsonValueNumber>(Point.Z)}; }
    bool ReadPointValue(const TSharedPtr<FJsonValue>& Value,FVector& Point)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;double Coordinates[3];
        if (!Value || !Value->TryGetArray(Values) || Values->Num()!=3) return false;
        for (int32 I=0;I<3;++I) if (!(*Values)[I]->TryGetNumber(Coordinates[I]) || !FMath::IsFinite(Coordinates[I])) return false;
        Point=FVector(Coordinates[0],Coordinates[1],Coordinates[2]);return true;
    }
    bool ReadPoint(const TSharedPtr<FJsonObject>& Object,const TCHAR* Key,FVector& Point)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
        if (!Object->TryGetArrayField(Key,Values) || Values->Num()!=3) return false;
        double Coordinates[3];
        for (int32 I=0;I<3;++I) if (!(*Values)[I]->TryGetNumber(Coordinates[I]) || !FMath::IsFinite(Coordinates[I])) return false;
        Point=FVector(Coordinates[0],Coordinates[1],Coordinates[2]);return true;
    }
    bool PerformanceSettingsValid(const TSharedPtr<FJsonObject>& Settings)
    {
        const auto Resolution=Settings->GetArrayField(TEXT("resolution"));
        return Settings->GetBoolField(TEXT("rendered")) && Resolution[0]->AsNumber()==1920 && Resolution[1]->AsNumber()==1080
            && Settings->GetNumberField(TEXT("screenPercentage"))==100 && Settings->GetNumberField(TEXT("maxFps"))==0
            && Settings->GetNumberField(TEXT("vSync"))==0 && Settings->GetNumberField(TEXT("dynamicResolutionMode"))==0
            && !Settings->GetBoolField(TEXT("frameSmoothing")) && !Settings->GetBoolField(TEXT("engineFixedFrameRate"))
            && !Settings->GetBoolField(TEXT("fappFixedTimeStep")) && Settings->GetNumberField(TEXT("worldTimeDilation"))==1;
    }
    bool HealNearby(AWarCharacter* Pawn,UWarAbilityRuntime* Runtime,const UWarAbilityCatalog* Catalog,AWarSiegeEncounter* Encounter)
    {
        if (!Pawn || !Catalog || Runtime->IsBusy()) return false;
        AWarCharacter* Injured=nullptr; float Lowest=.8f;
        for (TActorIterator<AWarCharacter> Other(Pawn->GetWorld());Other;++Other)
        {
            const auto* PS=Other->GetPlayerState<AWarPlayerState>(); const auto* Own=Pawn->GetPlayerState<AWarPlayerState>();
            if (!PS || !Own || PS->GetRealm()!=Own->GetRealm() || !Encounter->IsParticipant(*Other)
                || Other->IsDead() || FVector::Dist2D(Pawn->GetActorLocation(),Other->GetActorLocation())>1500 || PS->GetAttributes()->GetMaxHealth()<=0) continue;
            const float Fraction=PS->GetAttributes()->GetHealth()/PS->GetAttributes()->GetMaxHealth();
            if (Fraction<Lowest) { Lowest=Fraction; Injured=*Other; }
        }
        if (!Injured) return false;
        for (const auto* Ability:Catalog->Kit(Pawn->GetCareerId()))
            if (Ability->Effects.ContainsByPredicate([](const auto& E) { return E.Kind==TEXT("heal"); }) && Runtime->ReadyIn(Ability->Id)<=0)
            {
                FString Error;
                if (Ability->RequiresStationary())
                {
                    if (!Runtime->CanPrepareStationaryCast(*Ability,Injured,Error)) continue;
                    Pawn->GetCharacterMovement()->StopMovementImmediately(); Runtime->UpdateMovementIntent(false);
                }
                if (Runtime->TryActivate(Ability->Id,Injured,Error)) return true;
            }
        return false;
    }
}
bool UWarCitadelSiegeProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarCitadelSiegeProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentNetworking"));
#endif
}
bool UWarCitadelSiegeProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game; }
TStatId UWarCitadelSiegeProof::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCitadelSiegeProof, STATGROUP_Tickables); }
bool UWarCitadelSiegeProof::Load(FString& Error)
{
    FParse::Value(FCommandLine::Get(), TEXT("WarCitadelSiegeProofConfig="), ConfigPath);
    ConfigPath = FPaths::ConvertRelativePathToFull(ConfigPath);
    const FString Root = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("CitadelSiegeProof"));
    FString Text; TSharedPtr<FJsonObject> Config;
    if (!FPaths::IsUnderDirectory(ConfigPath, Root) || !FFileHelper::LoadFileToString(Text, *ConfigPath)
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Config) || !Config)
    { Error = TEXT("An exact private Saved/CitadelSiegeProof configuration is required."); return false; }
    bool ProofOnly = false;
    bPerformanceBaseline=FParse::Param(FCommandLine::Get(),TEXT("WarCitadelSiegePerformanceBaseline"));
    bool BaselineConfig=false,IsolatedWindows=false;FString FixtureMode;
    Config->TryGetBoolField(TEXT("performanceBaseline"),BaselineConfig);
    if (BaselineConfig!=bPerformanceBaseline || (bPerformanceBaseline &&
        (!Config->TryGetBoolField(TEXT("isolatedStageWindows"),IsolatedWindows) || IsolatedWindows
        || !Config->TryGetStringField(TEXT("fixtureMode"),FixtureMode) || FixtureMode!=BaselineFixtureMode
        || !FParse::Param(FCommandLine::Get(),TEXT("WarCitadelSiegePerformance")))))
    { Error=TEXT("A baseline requires explicit rendered earned progression without isolated stage initialization.");return false; }
    if (!Config->TryGetStringField(TEXT("map"), Map) || !Config->TryGetStringField(TEXT("cityRevision"), Revision)
        || !Config->TryGetStringField(TEXT("signature"), Signature) || !Config->TryGetStringField(TEXT("mapSha256"), MapHash)
        || !Config->TryGetBoolField(TEXT("proofOnly"), ProofOnly) || !ProofOnly
        || !Hex(Revision,64) || !Hex(Signature,64) || !Hex(MapHash,64)
        || !Map.StartsWith(TEXT("/Game/WorldRebuild/AegisCitadel_")) || Map.Contains(TEXT(".."))
        || (bPerformanceBaseline ? (!Map.EndsWith(TEXT("/PerformanceBaseline")) || Revision!=PreservedRevision
            || Map!=TEXT("/Game/WorldRebuild/AegisCitadel_")+Signature.Left(12)+TEXT("/PerformanceBaseline"))
            : (!Map.EndsWith(TEXT("/SiegeCandidate")) && !Map.EndsWith(TEXT("/CampaignCandidate"))))
        || GetWorld()->GetOutermost()->GetName() != Map)
    { Error = TEXT("Proof configuration does not identify this exact private candidate."); return false; }
    Config->TryGetBoolField(TEXT("contentReviewOverride"), bFixtureReview);
    bLive = Map.EndsWith(TEXT("/CampaignCandidate"));
    FString Outcome;
    if (Config->HasField(TEXT("campaignOutcome")))
    {
        if (!bLive || !Config->HasTypedField<EJson::String>(TEXT("campaignOutcome")) || !Config->TryGetStringField(TEXT("campaignOutcome"),Outcome)
            || (Outcome!=TEXT("city_captured") && Outcome!=TEXT("city_defended")))
        { Error=TEXT("A campaign outcome fixture requires an exact live candidate and a supported explicit result.");return false; }
        bLiveDefended=Outcome==TEXT("city_defended");
        if (bLiveDefended && (FParse::Param(FCommandLine::Get(),TEXT("WarCitadelSiegePerformance"))
            || FParse::Param(FCommandLine::Get(),TEXT("WarCitadelSiegeRecoveryProof"))))
        { Error=TEXT("The defended campaign fixture cannot substitute for three-stage performance or character recovery.");return false; }
    }
    if (bLive)
    {
        const TArray<TSharedPtr<FJsonValue>>* Ids=nullptr; TSet<FString> Seen;
        if (!Config->TryGetArrayField(TEXT("players"),Ids) || Ids->Num()!=36)
        { Error=TEXT("Live fixture needs exactly 36 explicitly provisioned synthetic character IDs."); return false; }
        for (int32 I=0;I<Ids->Num();++I)
        {
            FString Id; const FString Expected=TEXT("proof-")+Signature.Left(12)+(I<18 ? TEXT("-aegis-") : TEXT("-riftbound-"))+FString::FromInt(I%18);
            if (!(*Ids)[I]->TryGetString(Id) || Id!=Expected || Seen.Contains(Id))
            { Error=TEXT("Synthetic character IDs are not bound to the exact candidate fixture."); return false; }
            LiveIds.Add(Id); Seen.Add(Id);
        }
        LivePlayers.SetNum(36);
    }
    FString Filename;
    FString Digest;
    if (!FPackageName::DoesPackageExist(Map, &Filename))
    { Error = TEXT("The loaded candidate package is unavailable for its SHA-256 receipt."); return false; }
    if (!WarCitadelProofHash::File(Filename, Digest, Error)) return false;
    if (Digest != MapHash)
    { Error = TEXT("The loaded candidate package does not match its SHA-256 receipt."); return false; }
    if (!LoadPerformance(Config,Error) || !LoadRecovery(Config,Error)) return false;
    const bool DiagnosticFlag=FParse::Param(FCommandLine::Get(),TEXT("WarCitadelSiegeDiagnostic"));
    const bool DiagnosticConfig=Config->HasField(TEXT("diagnosticSeconds"));
    if (DiagnosticFlag!=DiagnosticConfig || (DiagnosticConfig &&
        (!Config->TryGetNumberField(TEXT("diagnosticSeconds"),DiagnosticSeconds) || !FMath::IsFinite(DiagnosticSeconds)
        || DiagnosticSeconds<60 || DiagnosticSeconds>600 || bLive || bPerformance || bRecoveryProof)))
    { Error=TEXT("A bounded diagnostic requires an isolated scenario, matching flag and 60-600 ordinary seconds.");return false; }
    Began = GetWorld()->GetTimeSeconds(); bLoaded = true; return true;
}

bool UWarCitadelSiegeProof::LoadRecovery(const TSharedPtr<FJsonObject>& Config,FString& Error)
{
    bRecoveryProof=FParse::Param(FCommandLine::Get(),TEXT("WarCitadelSiegeRecoveryProof"));
    bool RecoveryOnly=false;Config->TryGetBoolField(TEXT("recoveryOnly"),RecoveryOnly);
    if (RecoveryOnly!=bRecoveryProof)
    { Error=TEXT("Recovery requires its explicit private fixture flag and configuration.");return false; }
    if (!bRecoveryProof) return true;
    const TSharedPtr<FJsonObject>* Setup=nullptr;double Attempt=-1;FString HostFile,Url,Host;
    if (!bLive || bPerformance || !Config->TryGetObjectField(TEXT("recovery"),Setup)
        || (*Setup)->GetNumberField(TEXT("version"))!=1 || !(*Setup)->TryGetNumberField(TEXT("attempt"),Attempt)
        || Attempt<0 || Attempt>2 || Attempt!=FMath::FloorToDouble(Attempt)
        || !(*Setup)->TryGetStringField(TEXT("fixtureId"),RecoveryFixture) || RecoveryFixture.IsEmpty() || RecoveryFixture.Len()>64)
    { Error=TEXT("Only an exact live candidate can run the three-attempt native WAL recovery fixture.");return false; }
    for (TCHAR C:RecoveryFixture) if (!(FChar::IsLower(C) || FChar::IsDigit(C) || C=='_' || C=='-'))
    { Error=TEXT("Invalid private recovery fixture identity.");return false; }
    RecoveryConfig=*Setup;RecoveryAttempt=int32(Attempt);RecoveryConfigHash=FileHash(ConfigPath);
    const FString Directory=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("CitadelSiegeProof")/RecoveryFixture);
    if (!FPaths::IsSamePath(FPaths::GetPath(ConfigPath),Directory/(TEXT("attempt-")+FString::FromInt(RecoveryAttempt)))
        || !FParse::Value(FCommandLine::Get(),TEXT("WarCampaignSiegeHostConfig="),HostFile)
        || !FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(HostFile),Directory/TEXT("host.json")))
    { Error=TEXT("Recovery cannot share another host or native process configuration.");return false; }
    const auto HostConfig=WarScenarioTransport::ReadConfig(HostFile);bool Private=false;
    if (!HostConfig || !HostConfig->TryGetBoolField(TEXT("proofOnly"),Private) || !Private
        || !HostConfig->TryGetStringField(TEXT("hostId"),Host) || Host!=TEXT("citadel-proof-")+RecoveryFixture
        || HostConfig->GetStringField(TEXT("fixtureId"))!=RecoveryFixture || HostConfig->GetStringField(TEXT("map"))!=Map
        || HostConfig->GetStringField(TEXT("mapSha256"))!=MapHash || HostConfig->GetStringField(TEXT("signature"))!=Signature
        || HostConfig->GetStringField(TEXT("cityRevision"))!=Revision || !HostConfig->TryGetStringField(TEXT("url"),Url)
        || !Url.StartsWith(TEXT("http://127.0.0.1:")))
    { Error=TEXT("Recovery requires the matching private loopback owning-host authority.");return false; }
    FString Port=Url.Mid(17);int32 PortNumber=0;
    if (Port.IsEmpty() || !Port.IsNumeric() || !LexTryParseString(PortNumber,*Port) || PortNumber<1 || PortNumber>65535)
    { Error=TEXT("The recovery authority must use an explicit loopback port.");return false; }
    RecoveryHost=Host;
    const FTCHARToUTF8 HostBytes(*Host);uint8 HostDigest[20];FSHA1::HashBuffer(HostBytes.Get(),HostBytes.Length(),HostDigest);
    RecoveryWalDirectory=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("CampaignSiege/Wal")/BytesToHex(HostDigest,20).ToLower());
    for (int32 I=0;I<2;++I)
    {
        FString Receipt;const FString Expected=TextHash(RecoveryFixture+(I==0 ? TEXT(":reward-a") : TEXT(":reward-b"))).Left(32);
        if (!RecoveryConfig->TryGetStringField(I==0 ? TEXT("receiptA") : TEXT("receiptB"),Receipt) || Receipt!=Expected
            || !FGuid::ParseExact(Receipt,EGuidFormats::Digits,RecoveryReceipts[I]))
        { Error=TEXT("The trusted proof reward receipt is not bound to this private fixture.");return false; }
    }
    const TArray<TSharedPtr<FJsonValue>>* Expected=nullptr;
    if (!RecoveryConfig->TryGetArrayField(TEXT("expected"),Expected) || Expected->Num()!=RecoveryAttempt)
    { Error=TEXT("Every resumed attempt needs its original native mutation evidence.");return false; }
    for (int32 I=0;I<Expected->Num();++I)
    {
        const auto Row=(*Expected)[I]->AsObject();FString File,Hash;
        if (!Row || !Row->TryGetStringField(TEXT("path"),File) || !Row->TryGetStringField(TEXT("sha256"),Hash)
            || !Hex(Hash,64) || !FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(File),Directory/(TEXT("attempt-")+FString::FromInt(I))/TEXT("mutation.json"))
            || FileHash(File)!=Hash)
        { Error=TEXT("The original native mutation witness changed or is missing.");return false; }
        const auto Record=WarScenarioTransport::ReadConfig(File);
        if (!Record || Record->GetNumberField(TEXT("attempt"))!=I || Record->GetStringField(TEXT("fixtureId"))!=RecoveryFixture
            || Record->GetStringField(TEXT("map"))!=Map || Record->GetStringField(TEXT("signature"))!=Signature
            || Record->GetStringField(TEXT("mapSha256"))!=MapHash || !Record->GetBoolField(TEXT("mutationSucceeded"))
            || Record->GetObjectField(TEXT("after"))->GetStringField(TEXT("id"))!=LiveIds[0])
        { Error=TEXT("The recovery expectation is not a matching native mutation witness.");return false; }
        RecoveryExpected.Add(Record);
    }
    return CheckRecoveryBindings(Error);
}

bool UWarCitadelSiegeProof::CheckRecoveryBindings(FString& Error) const
{
    if (!RecoveryConfig || FileHash(ConfigPath)!=RecoveryConfigHash)
    { Error=TEXT("The native recovery configuration changed.");return false; }
    FString Binary,Hash,MapFile;
    if (!RecoveryConfig->TryGetStringField(TEXT("binaryPath"),Binary) || !RecoveryConfig->TryGetStringField(TEXT("binarySha256"),Hash)
        || !Hex(Hash,64) || !FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(Binary),FPaths::ConvertRelativePathToFull(FModuleManager::Get().GetModuleFilename(TEXT("AegisWar"))))
        || FileHash(Binary)!=Hash || !FPackageName::DoesPackageExist(Map,&MapFile) || FileHash(MapFile)!=MapHash)
    { Error=TEXT("The real recovery binary or candidate package differs from its binding.");return false; }
    const TSharedPtr<FJsonObject>* Sources=nullptr;
    const FString Root=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("Source"));bool Proof=false,Bridge=false;
    if (!RecoveryConfig->TryGetObjectField(TEXT("sourceHashes"),Sources) || (*Sources)->Values.IsEmpty() || (*Sources)->Values.Num()>1024)
    { Error=TEXT("Recovery requires bound native project sources.");return false; }
    for (const auto& Pair:(*Sources)->Values)
    {
        const FString Key(Pair.Key.Len(),*Pair.Key);const FString File=FPaths::ConvertRelativePathToFull(Key);FString Expected;
        if (!FPaths::IsUnderDirectory(File,Root) || !Pair.Value->TryGetString(Expected) || !Hex(Expected,64) || FileHash(File)!=Expected)
        { Error=TEXT("A native recovery source file changed.");return false; }
        Proof|=FPaths::IsSamePath(File,Root/TEXT("AegisWar/Private/WarCitadelSiegeProof.cpp"));
        Bridge|=FPaths::IsSamePath(File,Root/TEXT("AegisWar/Private/WarCampaignSiegeSubsystem.cpp"));
    }
    if (!Proof || !Bridge) { Error=TEXT("The actual proof and durability implementation must be hash-bound.");return false; }
    return true;
}

TSharedPtr<FJsonObject> UWarCitadelSiegeProof::RecoveryWitness(AWarPlayerController* Player) const
{
    auto Row=MakeShared<FJsonObject>();auto* PS=Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    const auto* Pawn=Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    Row->SetStringField(TEXT("characterId"),Player ? Player->ScenarioCharacterId : FString());
    Row->SetBoolField(TEXT("pending"),PS && PS->IsScenarioTransferPending());Row->SetBoolField(TEXT("member"),PS && PS->IsSiegeMember());
    Row->SetBoolField(TEXT("normalized"),PS && PS->IsSiegeNormalized());Row->SetNumberField(TEXT("combatLevel"),PS ? PS->GetCombatLevel() : 0);
    Row->SetStringField(TEXT("zone"),PS ? PS->GetCurrentZone().ToString() : FString());
    Row->SetBoolField(TEXT("alive"),Pawn && !Pawn->IsDead());Row->SetBoolField(TEXT("modelReady"),Pawn && Pawn->IsVisualReady());
    Row->SetBoolField(TEXT("movementHeld"),Pawn && Pawn->GetCharacterMovement()->MovementMode==MOVE_None);
    const auto* Streaming=GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    const bool SceneReady=PS && Streaming && Streaming->IsZoneReady(PS->GetCurrentZone(),Player);
    Row->SetBoolField(TEXT("sceneReady"),SceneReady);
    const auto* Zone=Pawn ? AWarZoneAnchor::FindAt(GetWorld(),Pawn->GetActorLocation()) : nullptr;
    const bool ZoneMatches=PS && Zone && Zone->ZoneId==PS->GetCurrentZone();Row->SetBoolField(TEXT("zoneMatches"),ZoneMatches);
    FVector Center;bool Physical=false;
    if (Pawn && SceneReady && ZoneMatches)
    {
        const auto* Capsule=Pawn->GetCapsuleComponent();const float Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
        Physical=FMath::IsNearlyEqual(Radius,42.f) && FMath::IsNearlyEqual(Half,96.f)
            && WarSiegeNavigation::SpawnCandidate(GetWorld(),Pawn->GetActorLocation()-FVector(0,0,Half+3),Radius,Half,Center,Pawn)
            && FVector::Dist2D(Center,Pawn->GetActorLocation())<=1 && FMath::Abs(Center.Z-Pawn->GetActorLocation().Z)<=5;
        Row->SetNumberField(TEXT("capsuleRadiusCm"),Radius);Row->SetNumberField(TEXT("capsuleHalfHeightCm"),Half);
        Row->SetArrayField(TEXT("position"),JsonPoint(Pawn->GetActorLocation()));Row->SetArrayField(TEXT("validatedCenter"),JsonPoint(Center));
    }
    Row->SetBoolField(TEXT("physicalReady"),Physical);
    const bool SafeReturn=Physical && PS && !PS->IsSiegeMember() && !PS->IsScenarioTransferPending() && !PS->IsSiegeNormalized()
        && Encounter && PS->GetCurrentZone()!=TEXT("aegis_capital") && Encounter->CanEvacuate(PS->GetRealm(),PS->GetCurrentZone());
    Row->SetBoolField(TEXT("safeReturn"),SafeReturn);return Row;
}

bool UWarCitadelSiegeProof::PrepareRecoveryCast(AWarPlayerController* Player,FString& Error)
{
    auto* PS=Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    auto* Pawn=Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    auto* Runtime=PS ? PS->GetClassAbilities() : nullptr;
    const auto* Status=UWarCombatStatus::On(Pawn);
    const auto* Catalog=GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    if (!PS || !Pawn || !Runtime || !Status || !Catalog || PS->IsScenarioTransferPending()) return false;
    if (RecoveryCastDefinition)
    {
        const bool Applied=Status->GetActive().ContainsByPredicate([&](const auto& S) {
            return S.AbilityId==RecoveryCastDefinition->Id && S.AppliedVersion==RecoveryCastDefinition->Version && S.Source==Pawn && S.Expires>Runtime->Now();
        });
        if (Applied && !Runtime->IsBusy() && Runtime->Cooldown(RecoveryCastDefinition->Id)>0) return true;
        if (Runtime->IsBusy() || Runtime->Cooldown(RecoveryCastDefinition->Id)>0) return false;
        RecoveryCastDefinition.Reset();RecoveryCastWitness.Reset();
    }
    TArray<const FWarAbilityDefinition*> Candidates;
    const auto Duration=[](const FWarAbilityDefinition& Ability) {
        float Maximum=0;for (const auto& E:Ability.Effects) Maximum=FMath::Max(Maximum,E.Duration);return Maximum;
    };
    for (const auto* Ability:Catalog->Kit(Pawn->GetCareerId()))
    {
        if (Ability->bEnemyTarget || Ability->Cooldown<=0 || (Ability->TargetKind!=TEXT("self") && Ability->TargetKind!=TEXT("ally"))
            || Ability->Effects.IsEmpty() || !Ability->Effects.ContainsByPredicate([](const auto& E) { return E.Kind==TEXT("player_status") && E.Duration>0; })
            || Ability->Effects.ContainsByPredicate([](const auto& E) { return E.Kind!=TEXT("player_status") || (!E.Recipient.IsNone() && E.Recipient!=TEXT("caster")); })) continue;
        Candidates.Add(Ability);
    }
    if (Candidates.IsEmpty()) { Error=TEXT("The real native class kit has no self-buff and cooldown suitable for this recovery fixture.");return false; }
    Candidates.Sort([&](const auto& A,const auto& B) { return Duration(A)>Duration(B); });
    for (const auto* Ability:Candidates)
    {
        FString Refusal,Payload,Hash;
        if (!Runtime->CanActivate(*Ability,Pawn,Refusal)) continue;
        if (!WarCampaignCombatDefinition::Encode(*Ability,Payload,Hash,Error)) return false;
        const int64 Started=WarCampaignCombatState::UnixMs();
        if (!Runtime->TryActivate(Ability->Id,Pawn,Refusal)) continue;
        RecoveryCastDefinition=MakeShared<const FWarAbilityDefinition>(*Ability);RecoveryCastWitness=MakeShared<FJsonObject>();
        RecoveryCastWitness->SetBoolField(TEXT("succeeded"),true);RecoveryCastWitness->SetStringField(TEXT("abilityId"),Ability->Id.ToString());
        RecoveryCastWitness->SetStringField(TEXT("career"),Ability->Career.ToString());RecoveryCastWitness->SetStringField(TEXT("version"),Ability->Version);
        RecoveryCastWitness->SetStringField(TEXT("definitionSha256"),Hash);RecoveryCastWitness->SetNumberField(TEXT("startedAtUnixMs"),Started);
        return false; // Normal animation/release must actually apply the status before the mutation.
    }
    return false;
}

TSharedPtr<FJsonObject> UWarCitadelSiegeProof::RecoveryWalCharacter(AWarPlayerController* Player,TSharedPtr<FJsonObject>& Witness,FString& Error) const
{
    Witness=nullptr;TSharedPtr<FJsonObject> Character;TArray<FString> Files;
    IFileManager::Get().FindFiles(Files,*(RecoveryWalDirectory/TEXT("*.json")),true,false);
    for (const FString& Name:Files)
    {
        const FString Filename=RecoveryWalDirectory/Name;
        const int64 Size=IFileManager::Get().FileSize(*Filename);TArray<uint8> Bytes;
        if (Size<0 || Size>1048576 || !FFileHelper::LoadFileToArray(Bytes,*Filename))
        { Error=TEXT("The actual flushed recovery WAL could not be read without changing it.");return nullptr; }
        const FUTF8ToTCHAR Utf8(reinterpret_cast<const ANSICHAR*>(Bytes.GetData()),Bytes.Num());
        const FString Text(Utf8.Length(),Utf8.Get());TSharedPtr<FJsonObject> Record;
        FString Host,Id,Activation,RequestId;double Schema=0,Base=0,Sequence=0;
        const TSharedPtr<FJsonObject>* Body=nullptr;
        if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Record) || !Record
            || !Record->TryGetStringField(TEXT("hostId"),Host) || Host!=RecoveryHost || !Record->TryGetObjectField(TEXT("body"),Body)
            || !(*Body)->TryGetStringField(TEXT("characterId"),Id))
        { Error=TEXT("The original recovery WAL is corrupt or belongs to another host.");return nullptr; }
        if (Id!=Player->ScenarioCharacterId) continue;
        FString Hash;
        if (Character || !Record->HasTypedField<EJson::Number>(TEXT("schemaVersion")) || !Record->TryGetNumberField(TEXT("schemaVersion"),Schema) || Schema!=1
            || !(*Body)->TryGetStringField(TEXT("hostId"),Host) || Host!=RecoveryHost || !Encounter
            || !(*Body)->TryGetStringField(TEXT("activationId"),Activation) || Activation!=Encounter->ActivationId
            || !(*Body)->TryGetStringField(TEXT("requestId"),RequestId) || RequestId.IsEmpty()
            || !WarCampaignCombatState::Number(*Body,TEXT("baseRevision"),Base,1,MAX_int32) || FMath::FloorToDouble(Base)!=Base
            || !WarCampaignCombatState::Number(*Body,TEXT("walSequence"),Sequence,1,MAX_int32) || FMath::FloorToDouble(Sequence)!=Sequence
            || !WarCitadelProofHash::Bytes(Bytes.GetData(),Bytes.Num(),Hash,Error))
        { Error=TEXT("The successful proof mutation does not identify one original owning-host WAL.");return nullptr; }
        const TSharedPtr<FJsonObject> *SavedCharacter=nullptr,*Document=nullptr,*Runtime=nullptr;double Version=0;
        if (!(*Body)->TryGetObjectField(TEXT("character"),SavedCharacter) || !(*SavedCharacter)->TryGetStringField(TEXT("id"),Id) || Id!=Player->ScenarioCharacterId
            || !(*SavedCharacter)->TryGetObjectField(TEXT("document"),Document) || !(*Document)->TryGetObjectField(TEXT("runtime"),Runtime)
            || !WarCampaignCombatState::Number(*Runtime,TEXT("version"),Version,2,2))
        { Error=TEXT("The flushed WAL does not contain the complete version-two character.");return nullptr; }
        Character=*SavedCharacter;
        Witness=MakeShared<FJsonObject>();Witness->SetStringField(TEXT("filename"),Name);Witness->SetStringField(TEXT("sha256"),Hash);
        Witness->SetStringField(TEXT("requestId"),RequestId);Witness->SetNumberField(TEXT("baseRevision"),Base);
        Witness->SetNumberField(TEXT("walSequence"),Sequence);
    }
    if (!Character) Error=TEXT("A successful native mutation has no original flushed WAL witness.");
    return Character;
}

void UWarCitadelSiegeProof::TickRecovery()
{
    FString Error;const double Now=GetWorld()->GetTimeSeconds();
    if (Now-Began>900) { FinishRecovery(false,TEXT("Native recovery or validated ordinary return remained incomplete; protected state is retained."));return; }
    if (!Round)
    {
        if (!Start(Error))
        {
            const FString Reason=!Error.IsEmpty() ? Error : Encounter && Encounter->bPreparing
                ? TEXT("The trusted encounter is still preparing.") : TEXT("The trusted encounter is not ready.");
            if (Reason!=LastStartupReason)
            {
                LastStartupReason=Reason;
                auto Record=MakeShared<FJsonObject>();Record->SetNumberField(TEXT("schemaVersion"),1);
                Record->SetBoolField(TEXT("diagnosticOnly"),true);Record->SetBoolField(TEXT("passed"),false);
                Record->SetStringField(TEXT("fixtureId"),RecoveryFixture);Record->SetNumberField(TEXT("attempt"),RecoveryAttempt);
                Record->SetStringField(TEXT("map"),Map);Record->SetStringField(TEXT("configSha256"),RecoveryConfigHash);
                Record->SetStringField(TEXT("reason"),Reason);Record->SetNumberField(TEXT("elapsedSeconds"),Now-Began);
                FString Text;FJsonSerializer::Serialize(Record,TJsonWriterFactory<>::Create(&Text));
                if (!FFileHelper::SaveStringToFile(Text,*(FPaths::GetPath(ConfigPath)/TEXT("startup-readiness.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
                { FinishRecovery(false,TEXT("Could not retain actual startup readiness evidence."));return; }
                UE_LOG(LogTemp,Display,TEXT("WAR_CITADEL_STARTUP_READINESS=%s"),*Reason);
            }
            if (Now-Began>240 && !Error.IsEmpty()) { FinishRecovery(false,Error);return; }
        }
    }
    auto* Target=LivePlayers.IsEmpty() ? nullptr : LivePlayers[0].Get();
    auto* PS=Target ? Target->GetPlayerState<AWarPlayerState>() : nullptr;
    if (Target)
    {
        const auto Witness=RecoveryWitness(Target);
        bRecoveryHeld|=Witness->GetBoolField(TEXT("pending")) && Witness->GetBoolField(TEXT("movementHeld"));
    }
    if (Now>=RecoveryNextProgress)
    {
        RecoveryNextProgress=Now+10;
        auto Progress=MakeShared<FJsonObject>();Progress->SetNumberField(TEXT("schemaVersion"),1);
        Progress->SetBoolField(TEXT("diagnosticOnly"),true);Progress->SetBoolField(TEXT("passed"),false);
        Progress->SetNumberField(TEXT("attempt"),RecoveryAttempt);Progress->SetStringField(TEXT("fixtureId"),RecoveryFixture);
        Progress->SetNumberField(TEXT("elapsedSeconds"),Now-Began);
        Progress->SetStringField(TEXT("configSha256"),RecoveryConfigHash);
        Progress->SetStringField(TEXT("encounterStatus"),Encounter ? Encounter->Status : LastStartupReason);
        TArray<TSharedPtr<FJsonValue>> Players;int32 Members=0,Pending=0,Safe=0;
        for (const auto& Weak:LivePlayers)
        {
            const auto Witness=RecoveryWitness(Weak.Get());Members+=Witness->GetBoolField(TEXT("member"));
            Pending+=Witness->GetBoolField(TEXT("pending"));Safe+=Witness->GetBoolField(TEXT("safeReturn"));
            Players.Add(MakeShared<FJsonValueObject>(Witness));
        }
        Progress->SetArrayField(TEXT("players"),Players);FString Text;
        FJsonSerializer::Serialize(Progress,TJsonWriterFactory<>::Create(&Text));
        // Unique immutable diagnostics avoid opening the authority's live journal.
        const FString File=FPaths::GetPath(ConfigPath)/FString::Printf(TEXT("progress-%03d.json"),RecoveryProgressSequence++);
        if (!FFileHelper::SaveStringToFile(Text,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
        { FinishRecovery(false,TEXT("Could not retain actual recovery readiness diagnostics."));return; }
        UE_LOG(LogTemp,Display,TEXT("WAR_CITADEL_RECOVERY_PROGRESS attempt=%d members=%d pending=%d safeReturns=%d"),RecoveryAttempt,Members,Pending,Safe);
    }
    if (!Round || !Encounter || !PS) return;
    auto* Bridge=GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>();if (!Bridge) return;
    if (!bRecoveryRestored)
    {
        for (const auto& Weak:LivePlayers)
        {
            auto* Player=Weak.Get();const auto Witness=RecoveryWitness(Player);
            if (!Witness->GetBoolField(TEXT("member")) || Witness->GetBoolField(TEXT("pending")) || Witness->GetBoolField(TEXT("normalized"))
                || Witness->GetNumberField(TEXT("combatLevel"))!=40 || !Witness->GetBoolField(TEXT("modelReady")) || !Witness->GetBoolField(TEXT("alive"))
                || !Witness->GetBoolField(TEXT("sceneReady")) || !Witness->GetBoolField(TEXT("physicalReady"))) return;
        }
        const auto Actual=WarScenarioTransport::Capture(Target,Target->ScenarioCharacterId,false,true,&Error);
        if (!Actual) return;
        if (RecoveryAttempt>0)
        {
            const auto Expected=RecoveryExpected.Last()->GetObjectField(TEXT("after"));
            FWarInventorySnapshot Inventory;FString Before,After;
            if (!FJsonObjectConverter::JsonObjectToUStruct(Expected->GetObjectField(TEXT("document"))->GetObjectField(TEXT("inventory")).ToSharedRef(),&Inventory,0,0)
                || !FJsonObjectConverter::UStructToJsonObjectString(Inventory,Before)
                || !FJsonObjectConverter::UStructToJsonObjectString(PS->GetInventory(),After) || Before!=After)
            { FinishRecovery(false,TEXT("The real restored native inventory differs from its original successful mutation."));return; }
            const auto Receipts=PS->CaptureScenarioState()->GetArrayField(TEXT("rewards"));
            const auto ExpectedReceipts=Expected->GetObjectField(TEXT("document"))->GetObjectField(TEXT("runtime"))->GetArrayField(TEXT("rewards"));
            TSet<FGuid> Seen,Required;
            for (const auto& Value:Receipts) { FGuid Id;if (FGuid::Parse(Value->AsString(),Id)) Seen.Add(Id); }
            for (const auto& Value:ExpectedReceipts) { FGuid Id;if (FGuid::Parse(Value->AsString(),Id)) Required.Add(Id); }
            bool Complete=Seen.Num()==Required.Num();for (const FGuid& Id:Required) Complete&=Seen.Contains(Id);
            if (!bRecoveryHeld || !Complete)
            { FinishRecovery(false,TEXT("Native recovery lost a reward receipt or released its movement hold without recorded recovery."));return; }
            auto Record=MakeShared<FJsonObject>();Record->SetNumberField(TEXT("schemaVersion"),1);Record->SetNumberField(TEXT("attempt"),RecoveryAttempt);
            Record->SetStringField(TEXT("fixtureId"),RecoveryFixture);Record->SetStringField(TEXT("map"),Map);Record->SetStringField(TEXT("signature"),Signature);
            Record->SetStringField(TEXT("configSha256"),RecoveryConfigHash);Record->SetBoolField(TEXT("heldObserved"),bRecoveryHeld);
            Record->SetObjectField(TEXT("character"),Actual);Record->SetObjectField(TEXT("witness"),RecoveryWitness(Target));
            FString Text;FJsonSerializer::Serialize(Record,TJsonWriterFactory<>::Create(&Text));
            if (!FFileHelper::SaveStringToFile(Text,*(FPaths::GetPath(ConfigPath)/TEXT("recovered.json"))))
            { FinishRecovery(false,TEXT("Could not save actual native recovery evidence."));return; }
        }
        bRecoveryRestored=true;
    }
    if (RecoveryAttempt<2)
    {
        if (bRecoveryMutation || Now<RecoveryNextMutation) return;RecoveryNextMutation=Now+.25;
        if (!PrepareRecoveryCast(Target,Error))
        { if (!Error.IsEmpty()) FinishRecovery(false,Error);return; }
        const auto Before=WarScenarioTransport::Capture(Target,Target->ScenarioCharacterId,false,true,&Error);if (!Before) return;
        if (!Bridge->JournalsMutations(PS) || !PS->GrantCharacterRewards(RecoveryReceipts[RecoveryAttempt],25,7,{},Error)) return;
        TSharedPtr<FJsonObject> WalWitness;const auto After=RecoveryWalCharacter(Target,WalWitness,Error);const auto Witness=RecoveryWitness(Target);
        if (!After || !Witness->GetBoolField(TEXT("pending")) || !Witness->GetBoolField(TEXT("movementHeld")))
        { FinishRecovery(false,Error.IsEmpty() ? TEXT("A successful real mutation did not retain the native durability hold.") : Error);return; }
        const auto Runtime=After->GetObjectField(TEXT("document"))->GetObjectField(TEXT("runtime"));
        TArray<TSharedPtr<FJsonValue>> StatusIds;double CastCooldown=0;
        for (const auto& Value:Runtime->GetObjectField(TEXT("combat"))->GetArrayField(TEXT("statuses")))
        {
            const auto Row=Value->AsObject();
            if (Row->GetStringField(TEXT("abilityId"))==RecoveryCastDefinition->Id.ToString() && Row->GetStringField(TEXT("appliedVersion"))==RecoveryCastDefinition->Version
                && Row->GetStringField(TEXT("definitionSha256"))==RecoveryCastWitness->GetStringField(TEXT("definitionSha256")))
                StatusIds.Add(MakeShared<FJsonValueString>(Row->GetStringField(TEXT("id"))));
        }
        for (const auto& Value:Runtime->GetObjectField(TEXT("abilities"))->GetArrayField(TEXT("cooldowns")))
            if (Value->AsObject()->GetStringField(TEXT("id"))==RecoveryCastDefinition->Id.ToString()) CastCooldown=Value->AsObject()->GetNumberField(TEXT("expiresAtUnixMs"));
        if (StatusIds.IsEmpty() || CastCooldown<=Runtime->GetNumberField(TEXT("capturedAtUnixMs")))
        { FinishRecovery(false,TEXT("The real cast expired before its successful mutation could flush effects and cooldowns; its WAL remains protected."));return; }
        RecoveryCastWitness->SetArrayField(TEXT("statusIds"),StatusIds);RecoveryCastWitness->SetNumberField(TEXT("cooldownExpiresAtUnixMs"),CastCooldown);
        RecoveryCastWitness->SetNumberField(TEXT("observedAtUnixMs"),Runtime->GetNumberField(TEXT("capturedAtUnixMs")));
        auto Record=MakeShared<FJsonObject>();Record->SetNumberField(TEXT("schemaVersion"),1);Record->SetNumberField(TEXT("attempt"),RecoveryAttempt);
        Record->SetStringField(TEXT("fixtureId"),RecoveryFixture);Record->SetStringField(TEXT("map"),Map);Record->SetStringField(TEXT("signature"),Signature);
        Record->SetStringField(TEXT("mapSha256"),MapHash);Record->SetStringField(TEXT("cityRevision"),Revision);Record->SetStringField(TEXT("configSha256"),RecoveryConfigHash);
        Record->SetStringField(TEXT("receipt"),RecoveryReceipts[RecoveryAttempt].ToString());Record->SetBoolField(TEXT("mutationSucceeded"),true);
        Record->SetObjectField(TEXT("before"),Before);Record->SetObjectField(TEXT("after"),After);Record->SetObjectField(TEXT("witness"),Witness);
        Record->SetObjectField(TEXT("cast"),RecoveryCastWitness);Record->SetObjectField(TEXT("wal"),WalWitness);
        FString Text;FJsonSerializer::Serialize(Record,TJsonWriterFactory<>::Create(&Text));
        if (!FFileHelper::SaveStringToFile(Text,*(FPaths::GetPath(ConfigPath)/TEXT("mutation.json"))))
        { FinishRecovery(false,TEXT("Could not save the real native mutation witness; its original WAL stays protected."));return; }
        bRecoveryMutation=true;return;
    }
    if (!bRecoveryMutation)
    {
        const int32 InventoryRevision=PS->GetInventory().Revision;
        if (PS->GrantCharacterRewards(RecoveryReceipts[1],25,7,{},Error) || PS->GetInventory().Revision!=InventoryRevision)
        { FinishRecovery(false,TEXT("A recovered reward transaction was granted a second time."));return; }
        bRecoveryMutation=true;
    }
    bool Returned=true;
    for (const auto& Weak:LivePlayers)
    {
        auto* Player=Weak.Get();auto* State=Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        if (!State) { Returned=false;continue; }
        if (State->IsSiegeMember() && !State->IsScenarioTransferPending() && !RecoveryLeaveRequested.Contains(Player->ScenarioCharacterId))
        { Bridge->Enroll(Player,false);RecoveryLeaveRequested.Add(Player->ScenarioCharacterId); }
        const auto Witness=RecoveryWitness(Player);
        Returned&=Witness->GetBoolField(TEXT("safeReturn")) && Witness->GetBoolField(TEXT("alive")) && Witness->GetBoolField(TEXT("modelReady"));
    }
    if (Returned) FinishRecovery(true,TEXT("Actual native WAL replay, protected character recovery and validated normal return completed; no siege outcome was claimed."));
}

void UWarCitadelSiegeProof::FinishRecovery(bool Passed,const FString& Detail)
{
    bFinished=true;FString Error;Passed&=CheckRecoveryBindings(Error);
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("schemaVersion"),1);Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetBoolField(TEXT("recoveryOnly"),true);Report->SetBoolField(TEXT("proofOnly"),true);Report->SetNumberField(TEXT("attempt"),RecoveryAttempt);
    Report->SetStringField(TEXT("fixtureId"),RecoveryFixture);Report->SetStringField(TEXT("map"),Map);Report->SetStringField(TEXT("mapSha256"),MapHash);
    Report->SetStringField(TEXT("cityRevision"),Revision);Report->SetStringField(TEXT("signature"),Signature);Report->SetStringField(TEXT("configSha256"),RecoveryConfigHash);
    Report->SetStringField(TEXT("detail"),Error.IsEmpty() ? Detail : Error);Report->SetBoolField(TEXT("heldObserved"),bRecoveryHeld);
    TArray<TSharedPtr<FJsonValue>> Witnesses,Characters;
    for (const auto& Weak:LivePlayers) if (auto* Player=Weak.Get())
    {
        Witnesses.Add(MakeShared<FJsonValueObject>(RecoveryWitness(Player)));
        if (auto Character=WarScenarioTransport::Capture(Player,Player->ScenarioCharacterId,true,true,&Error)) Characters.Add(MakeShared<FJsonValueObject>(Character));
        else Passed=false;
    }
    Report->SetArrayField(TEXT("returnWitnesses"),Witnesses);Report->SetArrayField(TEXT("characters"),Characters);
    Report->SetBoolField(TEXT("passed"),Passed);
    if (!Error.IsEmpty()) Report->SetStringField(TEXT("detail"),Error);
    if (RecoveryConfig) Report->SetObjectField(TEXT("bindings"),RecoveryConfig);
    if (Encounter) Report->SetObjectField(TEXT("unfinishedSiege"),UWarCampaignSiegeSubsystem::Snapshot(Encounter->Siege,Encounter->bPreparing));
    for (const TCHAR* Flag:{TEXT("productionAdmission"),TEXT("steamAdmission"),TEXT("humanPlaytest"),TEXT("visualApproval"),TEXT("releaseAcceptance"),
        TEXT("progressionAcceptance"),TEXT("victoryAcceptance"),TEXT("conquestAcceptance"),TEXT("routeAcceptance"),TEXT("fullSiegeAdmission")}) Report->SetBoolField(Flag,false);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
    if (!FFileHelper::SaveStringToFile(Text,*(FPaths::GetPath(ConfigPath)/TEXT("recovery-report.json")))) Passed=false;
    UE_LOG(LogTemp,Display,TEXT("WAR_CITADEL_RECOVERY_PROOF passed=%d attempt=%d detail=%s"),Passed,RecoveryAttempt,*Detail);
    FPlatformMisc::RequestExitWithStatus(false,Passed ? 0 : 1);
}

bool UWarCitadelSiegeProof::CheckPerformanceBindings(FString& Error) const
{
    if (!PerformanceBindings || PerformanceConfigHash.IsEmpty() || FileHash(ConfigPath)!=PerformanceConfigHash)
    { Error=TEXT("The performance proof configuration changed.");return false; }
    FString MapFile;
    if (!FPackageName::DoesPackageExist(Map,&MapFile) || FileHash(MapFile)!=MapHash)
    { Error=TEXT("The actual performance map package changed during the native run.");return false; }
    const FString SavedRoot=FPaths::ConvertRelativePathToFull(FPaths::GetPath(ConfigPath));
    const FString Repository=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("../.."));
    const auto BoundFile=[&](const TCHAR* PathKey,const TCHAR* HashKey,const FString& Root)
    {
        FString Filename,Expected;
        return PerformanceBindings->TryGetStringField(PathKey,Filename) && PerformanceBindings->TryGetStringField(HashKey,Expected)
            && Hex(Expected,64) && FPaths::IsUnderDirectory(FPaths::ConvertRelativePathToFull(Filename),Root) && FileHash(Filename)==Expected;
    };
    FString SettingsFile;
    if (!BoundFile(TEXT("settingsPath"),TEXT("settingsSha256"),SavedRoot)
        || !PerformanceBindings->TryGetStringField(TEXT("settingsPath"),SettingsFile)
        || !FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(SettingsFile),FPaths::ConvertRelativePathToFull(GGameUserSettingsIni))
        || !BoundFile(TEXT("blueprintPath"),TEXT("blueprintSha256"),Repository/TEXT("artifacts/unreal/aegis-citadel")))
    { Error=TEXT("The active isolated performance settings or signed blueprint differ from the receipt.");return false; }
    FString Binary,Expected;
    const FString LoadedBinary=FPaths::ConvertRelativePathToFull(FModuleManager::Get().GetModuleFilename(TEXT("AegisWar")));
    if (!PerformanceBindings->TryGetStringField(TEXT("binaryPath"),Binary) || !PerformanceBindings->TryGetStringField(TEXT("binarySha256"),Expected)
        || !FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(Binary),LoadedBinary) || !Hex(Expected,64) || FileHash(Binary)!=Expected)
    { Error=TEXT("The loaded native module does not match the performance binary receipt.");return false; }
    const TSharedPtr<FJsonObject>* Sources=nullptr;
    if (!PerformanceBindings->TryGetObjectField(TEXT("sourceHashes"),Sources) || (*Sources)->Values.IsEmpty() || (*Sources)->Values.Num()>1024)
    { Error=TEXT("A bounded native project source hash map is required.");return false; }
    const FString SourceRoot=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("Source"));
    const FString Private=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("Source/AegisWar/Private/WarCitadelSiegeProof.cpp"));
    const FString Public=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("Source/AegisWar/Public/WarCitadelSiegeProof.h"));
    bool BoundPrivate=false,BoundPublic=false;
    for (const auto& Pair:(*Sources)->Values)
    {
        const FString Key(Pair.Key.Len(),*Pair.Key);
        if (Key.Contains(TEXT("\n")) || Key.Contains(TEXT("\r"))) { Error=TEXT("Invalid native source receipt path.");return false; }
        const FString Filename=FPaths::ConvertRelativePathToFull(Key);
        const FString Extension=FPaths::GetExtension(Filename).ToLower();
        FString SourceHash;
        if (!FPaths::IsUnderDirectory(Filename,SourceRoot) || (Extension!=TEXT("cpp") && Extension!=TEXT("h") && Extension!=TEXT("cs"))
            || !Pair.Value->TryGetString(SourceHash) || !Hex(SourceHash,64) || FileHash(Filename)!=SourceHash)
        { Error=TEXT("The performance proof source differs from its bound native run.");return false; }
        BoundPrivate|=FPaths::IsSamePath(Filename,Private);BoundPublic|=FPaths::IsSamePath(Filename,Public);
    }
    if (!BoundPrivate || !BoundPublic) { Error=TEXT("Both native performance proof source files must be hash-bound.");return false; }
    const TSharedPtr<FJsonObject>* Configs=nullptr;
    if (!PerformanceBindings->TryGetObjectField(TEXT("configHashes"),Configs) || (*Configs)->Values.IsEmpty() || (*Configs)->Values.Num()>32)
    { Error=TEXT("The normal graphics seed and engine configuration hashes are required.");return false; }
    bool BoundEngine=false,BoundSeed=false;
    for (const auto& Pair:(*Configs)->Values)
    {
        const FString Key(Pair.Key.Len(),*Pair.Key);
        if (Key.Contains(TEXT("\n")) || Key.Contains(TEXT("\r"))) { Error=TEXT("Invalid native graphics receipt path.");return false; }
        const FString Filename=FPaths::ConvertRelativePathToFull(Key);FString ConfigHash;
        const bool Engine=FPaths::IsSamePath(Filename,FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("Config/DefaultEngine.ini")));
        const bool Seed=FPaths::IsUnderDirectory(Filename,FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Config")));
        if ((!Engine && !Seed) || !Pair.Value->TryGetString(ConfigHash) || !Hex(ConfigHash,64) || FileHash(Filename)!=ConfigHash)
        { Error=TEXT("The normal engine or graphics configuration changed.");return false; }
        BoundEngine|=Engine;BoundSeed|=Seed;
    }
    if (!BoundEngine || !BoundSeed) { Error=TEXT("The benchmark must retain the normal graphics seed and engine configuration.");return false; }
    return !PerformanceBaselineManifest || CheckBaselineBindings(Error);
}

bool UWarCitadelSiegeProof::CheckBaselineBindings(FString& Error) const
{
    if (!bPerformanceBaseline || !PerformanceBaselineManifest || !PerformanceBlueprint)
    { Error=TEXT("The preserved-city baseline manifest is unavailable.");return false; }
    const FString ExpectedManifest=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("../../artifacts/unreal/aegis-citadel/performance-baseline")/Signature.Left(12)/TEXT("baseline.json"));
    if (!FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(PerformanceBindings->GetStringField(TEXT("blueprintPath"))),ExpectedManifest))
    { Error=TEXT("The baseline manifest is outside its exact signed private fixture directory.");return false; }
    const TSharedPtr<FJsonObject>* City=nullptr;const TSharedPtr<FJsonObject>* Owned=nullptr;
    const TSharedPtr<FJsonObject>* Sources=nullptr;const TSharedPtr<FJsonObject>* Dependencies=nullptr;
    if (!PerformanceBlueprint->TryGetObjectField(TEXT("sourceCity"),City) || (*City)->GetStringField(TEXT("path"))!=PreservedCity
        || (*City)->GetStringField(TEXT("revision"))!=PreservedRevision
        || !PerformanceBaselineManifest->TryGetObjectField(TEXT("packageHashes"),Owned) || (*Owned)->Values.IsEmpty() || (*Owned)->Values.Num()>32
        || !PerformanceBlueprint->TryGetObjectField(TEXT("sourceHashes"),Sources) || (*Sources)->Values.IsEmpty()
        || !PerformanceBlueprint->TryGetObjectField(TEXT("dependencyHashes"),Dependencies)
        || (*Sources)->Values.Num()+(*Dependencies)->Values.Num()>8192)
    { Error=TEXT("The baseline does not bind the preserved city and all original scenery packages.");return false; }
    TSet<FName> OriginalPackages;
    const auto VerifyPackages=[&](const TSharedPtr<FJsonObject>& Packages,bool PrivateOverlay)
    {
        for (const auto& Pair:Packages->Values)
        {
            const FString Package(Pair.Key.Len(),*Pair.Key);
            const bool Private=Package.StartsWith(TEXT("/Game/WorldRebuild/AegisCitadel_")+Signature.Left(12)+TEXT("/"));
            FString Expected,Filename;
            if (!FPackageName::IsValidLongPackageName(Package,true) || PrivateOverlay!=Private
                || (!Package.StartsWith(TEXT("/Game/")) && !Package.StartsWith(TEXT("/Engine/")))
                || !Pair.Value->TryGetString(Expected) || !Hex(Expected,64)
                || !FPackageName::DoesPackageExist(Package,&Filename) || FileHash(Filename)!=Expected) return false;
            if (!PrivateOverlay) OriginalPackages.Add(FName(*Package));
        }
        return true;
    };
    if (!VerifyPackages(*Owned,true) || !(*Owned)->HasField(Map) || (*Owned)->GetStringField(Map)!=MapHash
        || !VerifyPackages(*Sources,false) || !VerifyPackages(*Dependencies,false) || !(*Sources)->HasField(PreservedCity))
    { Error=TEXT("An owned overlay or original preserved-city package differs from its byte receipt.");return false; }
    const auto* Definition=LoadObject<UWarCityDefinition>(nullptr,*(FString(PreservedCity)+TEXT(".City")));
    if (!Definition || Definition->Revision!=PreservedRevision || Definition->SceneryLevels.IsEmpty())
    { Error=TEXT("The baseline cannot load its unchanged published city definition.");return false; }
    TArray<FName> Pending{FName(PreservedCity)};TSet<FName> Seen;
    for (FName Package:Definition->Packages())
    {
        if (!(*Sources)->HasField(Package.ToString()))
        { Error=TEXT("A published scenery level is missing from baseline source hashes.");return false; }
        Pending.Add(Package);
    }
    auto& Registry=FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
    while (!Pending.IsEmpty())
    {
        const FName Package=Pending.Pop(EAllowShrinking::No);if (Seen.Contains(Package)) continue;Seen.Add(Package);
        if (Seen.Num()>8192 || !OriginalPackages.Contains(Package))
        { Error=TEXT("The original city's native dependency closure is not fully hash-bound.");return false; }
        TArray<FName> Children;
        if (!Registry.GetDependencies(Package,Children,UE::AssetRegistry::EDependencyCategory::Package))
        { Error=TEXT("The native asset registry cannot verify an original baseline package dependency set.");return false; }
        for (FName Child:Children)
        {
            const FString Name=Child.ToString();
            if (Name.StartsWith(TEXT("/Game/")) || Name.StartsWith(TEXT("/Engine/"))) Pending.Add(Child);
        }
    }
    return true;
}

TSharedPtr<FJsonObject> UWarCitadelSiegeProof::PerformanceSettings() const
{
    auto Settings=MakeShared<FJsonObject>();
    const auto CVar=[](const TCHAR* Name) { const auto* Variable=IConsoleManager::Get().FindConsoleVariable(Name);return Variable ? double(Variable->GetFloat()) : -1.; };
    const bool Rendered=FApp::CanEverRender() && GDynamicRHI && RHIGetInterfaceType()!=ERHIInterfaceType::Null
        && GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport;
    const FIntPoint Resolution=Rendered ? GEngine->GameViewport->Viewport->GetSizeXY() : FIntPoint::ZeroValue;
    Settings->SetBoolField(TEXT("rendered"),Rendered);
    Settings->SetArrayField(TEXT("resolution"),{MakeShared<FJsonValueNumber>(Resolution.X),MakeShared<FJsonValueNumber>(Resolution.Y)});
    Settings->SetNumberField(TEXT("screenPercentage"),CVar(TEXT("r.ScreenPercentage")));
    Settings->SetNumberField(TEXT("maxFps"),CVar(TEXT("t.MaxFPS")));Settings->SetNumberField(TEXT("vSync"),CVar(TEXT("r.VSync")));
    Settings->SetNumberField(TEXT("dynamicResolutionMode"),CVar(TEXT("r.DynamicRes.OperationMode")));
    Settings->SetBoolField(TEXT("frameSmoothing"),GEngine && GEngine->bSmoothFrameRate);
    Settings->SetBoolField(TEXT("engineFixedFrameRate"),GEngine && GEngine->bUseFixedFrameRate);
    Settings->SetBoolField(TEXT("fappFixedTimeStep"),FApp::UseFixedTimeStep());
    Settings->SetNumberField(TEXT("worldTimeDilation"),GetWorld()->GetWorldSettings()->GetEffectiveTimeDilation());
    Settings->SetStringField(TEXT("rhi"),GDynamicRHI ? GDynamicRHI->GetName() : TEXT("Unavailable"));
    Settings->SetStringField(TEXT("gameUserSettingsIni"),FPaths::ConvertRelativePathToFull(GGameUserSettingsIni));
    auto Quality=MakeShared<FJsonObject>();
    for (const TCHAR* Name:{TEXT("sg.ViewDistanceQuality"),TEXT("sg.AntiAliasingQuality"),TEXT("sg.ShadowQuality"),TEXT("sg.GlobalIlluminationQuality"),
        TEXT("sg.ReflectionQuality"),TEXT("sg.PostProcessQuality"),TEXT("sg.TextureQuality"),TEXT("sg.EffectsQuality"),TEXT("sg.FoliageQuality"),TEXT("sg.ShadingQuality"),TEXT("sg.LandscapeQuality")})
        Quality->SetNumberField(Name,CVar(Name));
    Settings->SetObjectField(TEXT("quality"),Quality);return Settings;
}

bool UWarCitadelSiegeProof::LoadPerformance(const TSharedPtr<FJsonObject>& Config,FString& Error)
{
    bPerformance=FParse::Param(FCommandLine::Get(),TEXT("WarCitadelSiegePerformance"));
    if (!bPerformance) return true;
    const TSharedPtr<FJsonObject>* Setup=nullptr;const TArray<TSharedPtr<FJsonValue>>* Cameras=nullptr;
    if (!Config->TryGetObjectField(TEXT("performance"),Setup) || (*Setup)->GetNumberField(TEXT("version"))!=1
        || (*Setup)->GetNumberField(TEXT("settleSeconds"))!=10 || (*Setup)->GetNumberField(TEXT("minWindowSeconds"))!=60
        || !(*Setup)->TryGetArrayField(TEXT("cameras"),Cameras) || Cameras->Num()!=3)
    { Error=TEXT("An explicit rendered performance configuration with three physical-stage cameras is required.");return false; }
    PerformanceBindings=*Setup;PerformanceConfigHash=FileHash(ConfigPath);PerformanceCameras=*Cameras;
    if (!CheckPerformanceBindings(Error)) return false;
    FString BlueprintText;TSharedPtr<FJsonObject> SourceDocument;const TArray<TSharedPtr<FJsonValue>>* Formations=nullptr;
    if (!FFileHelper::LoadFileToString(BlueprintText,*PerformanceBindings->GetStringField(TEXT("blueprintPath")))
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(BlueprintText),SourceDocument) || !SourceDocument)
    { Error=TEXT("The exact signed source must explicitly author all three benchmark formations.");return false; }
    if (bPerformanceBaseline)
    {
        FString Payload,FixtureMode;bool Baseline=false,Isolated=false;
        if (!SourceDocument->TryGetBoolField(TEXT("performanceBaseline"),Baseline) || !Baseline
            || !SourceDocument->TryGetBoolField(TEXT("isolatedStageWindows"),Isolated) || Isolated
            || !SourceDocument->TryGetStringField(TEXT("fixtureMode"),FixtureMode) || FixtureMode!=BaselineFixtureMode
            || SourceDocument->GetNumberField(TEXT("schemaVersion"))!=1 || SourceDocument->GetStringField(TEXT("signature"))!=Signature
            || SourceDocument->GetStringField(TEXT("map"))!=Map || SourceDocument->GetStringField(TEXT("geometrySignature"))!=PreservedRevision
            || !SourceDocument->TryGetStringField(TEXT("signaturePayload"),Payload) || TextHash(Payload)!=Signature
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Payload),PerformanceBlueprint) || !PerformanceBlueprint)
        { Error=TEXT("The baseline signature does not bind its original scenery, functional cameras and mapped anchors.");return false; }
        if (!PerformanceBlueprint->TryGetStringField(TEXT("fixtureMode"),FixtureMode) || FixtureMode!=BaselineFixtureMode)
        { Error=TEXT("The signed baseline payload does not require authentic earned progression.");return false; }
        PerformanceBaselineManifest=SourceDocument;
        if (!CheckBaselineBindings(Error)) return false;
    }
    else
    {
        PerformanceBlueprint=SourceDocument;
        if (PerformanceBlueprint->GetStringField(TEXT("signature"))!=Signature)
        { Error=TEXT("The benchmark source belongs to another candidate.");return false; }
    }
    if (!PerformanceBlueprint->TryGetArrayField(TEXT("performanceFormations"),Formations) || Formations->Num()!=3)
    { Error=TEXT("The signed source must explicitly author all three benchmark formations.");return false; }
    TSet<int32> FormationStages;
    for (int32 Stage=0;Stage<3;++Stage)
    {
        const auto Camera=PerformanceCameras[Stage]->AsObject();FVector Eye,Target;
        double FieldOfView=0;const TArray<TSharedPtr<FJsonValue>>* PositionsForStage=nullptr;
        if (!Camera || Camera->GetNumberField(TEXT("stage"))!=Stage || !ReadPoint(Camera,TEXT("eye"),Eye)
            || !ReadPoint(Camera,TEXT("target"),Target) || !Camera->TryGetNumberField(TEXT("fieldOfView"),FieldOfView)
            || FieldOfView<10 || FieldOfView>120 || Eye.Z<Target.Z+1000
            || !Camera->TryGetArrayField(TEXT("positions"),PositionsForStage) || PositionsForStage->Num()!=36)
        { Error=TEXT("Invalid rendered crowd camera.");return false; }
        TSharedPtr<FJsonObject> Formation;
        for (const auto& Value:*Formations)
        {
            const auto Object=Value->AsObject();double SourceStage=-1;
            if (!Object || !Object->TryGetNumberField(TEXT("stage"),SourceStage) || !FMath::IsFinite(SourceStage)
                || SourceStage<0 || SourceStage>2 || SourceStage!=FMath::FloorToInt(SourceStage))
            { Error=TEXT("Invalid signed formation stage.");return false; }
            if (SourceStage==Stage) { if (Formation) { Error=TEXT("Duplicate signed formation stage.");return false; } Formation=Object; }
        }
        const TArray<TSharedPtr<FJsonValue>>* SourcePositions=nullptr;double CaptureGap=0;
        if (!Formation || !Formation->TryGetNumberField(TEXT("minimumCaptureGapCm"),CaptureGap) || CaptureGap!=50
            || !Formation->TryGetArrayField(TEXT("positions"),SourcePositions) || SourcePositions->Num()!=36 || FormationStages.Contains(Stage))
        { Error=TEXT("Signed formations must contain 36 distinct player positions outside capture rings.");return false; }
        const TSharedPtr<FJsonObject>* SourceCamera=nullptr;FVector SourceEye,SourceTarget;double SourceFov=0;
        if (!Formation->TryGetObjectField(TEXT("camera"),SourceCamera) || !ReadPoint(*SourceCamera,TEXT("eye"),SourceEye)
            || !ReadPoint(*SourceCamera,TEXT("target"),SourceTarget) || !(*SourceCamera)->TryGetNumberField(TEXT("horizontalFovDegrees"),SourceFov)
            || !Eye.Equals(SourceEye,.01) || !Target.Equals(SourceTarget,.01) || FieldOfView!=SourceFov)
        { Error=TEXT("The functional benchmark camera differs from the signed formation camera.");return false; }
        FormationStages.Add(Stage);
        for (int32 Slot=0;Slot<36;++Slot)
        {
            FVector ConfigPoint,SourcePoint;
            if (!ReadPointValue((*PositionsForStage)[Slot],ConfigPoint) || !ReadPointValue((*SourcePositions)[Slot],SourcePoint)
                || !ConfigPoint.Equals(SourcePoint,.01))
            { Error=TEXT("Benchmark orders differ from the signed source formation.");return false; }
            for (int32 Earlier=0;Earlier<Slot;++Earlier)
            {
                FVector EarlierPoint;ReadPointValue((*SourcePositions)[Earlier],EarlierPoint);
                if (FVector::Dist2D(SourcePoint,EarlierPoint)<134)
                { Error=TEXT("Signed benchmark player positions overlap their normal crowd clearance.");return false; }
            }
        }
        auto Window=MakeShared<FJsonObject>();Window->SetNumberField(TEXT("stage"),Stage);
        Window->SetNumberField(TEXT("startElapsedSeconds"),0);Window->SetNumberField(TEXT("endElapsedSeconds"),0);
        Window->SetNumberField(TEXT("frameCount"),0);Window->SetNumberField(TEXT("settleSeconds"),10);
        PerformanceWindows.Add(MakeShared<FJsonValueObject>(Window));
    }
    if (!PerformanceSettingsValid(PerformanceSettings()))
    { Error=TEXT("Performance requires real uncapped 1920x1080 rendering at 100%, without VSync, smoothing, fixed time or dilation.");return false; }
    PerformanceHardware=MakeShared<FJsonObject>();
    PerformanceHardware->SetStringField(TEXT("cpu"),FPlatformMisc::GetCPUBrand());
    PerformanceHardware->SetStringField(TEXT("gpu"),FPlatformMisc::GetPrimaryGPUBrand());
    PerformanceHardware->SetStringField(TEXT("adapter"),GRHIAdapterName);
    PerformanceHardware->SetStringField(TEXT("driverVersion"),GRHIAdapterUserDriverVersion);
    PerformanceHardware->SetStringField(TEXT("os"),FPlatformMisc::GetOSVersion());
    PerformanceHardware->SetStringField(TEXT("engineVersion"),FEngineVersion::Current().ToString());
    PerformanceHardware->SetNumberField(TEXT("physicalMemoryBytes"),double(FPlatformMemory::GetConstants().TotalPhysical));
    PerformanceFramesPath=FPaths::GetPath(ConfigPath)/TEXT("performance-frames.json");
    PerformanceWriter.Reset(IFileManager::Get().CreateFileWriter(*PerformanceFramesPath,FILEWRITE_NoReplaceExisting));
    if (!PerformanceWriter) { Error=TEXT("Cannot create fresh native performance frame evidence.");return false; }
    const FTCHARToUTF8 Prefix(TEXT("{\"schemaVersion\":1,\"frames\":["));
    PerformanceWriter->Serialize(const_cast<ANSICHAR*>(Prefix.Get()),Prefix.Length());
    PerformanceBegan=FPlatformTime::Seconds();PerformancePrevious=PerformanceBegan;return true;
}

bool UWarCitadelSiegeProof::ObserveBaselineProgression(FString& Error,bool Force)
{
    if (!bPerformanceBaseline) return true;
    if (!Encounter || !Encounter->Battlefield)
    { Error=TEXT("The earned baseline encounter is unavailable.");return false; }
    const auto& State=Encounter->Siege;
    int32 Claims=0;for (int32 Bit=0;Bit<7;++Bit) Claims+=(State.MainClaims>>Bit)&1;
    const bool StageClaims=State.Stage==0 ? (State.MainClaims==0 || State.MainClaims==1 || State.MainClaims==3 || State.MainClaims==7 || State.MainClaims==15)
        : State.Stage==1 ? (State.MainClaims==15 || State.MainClaims==31 || State.MainClaims==47 || State.MainClaims==63 || State.MainClaims==127)
        : State.Stage==2 && State.MainClaims==127;
    if (State.RulesVersion!=2 || State.Capacity!=18 || State.Scenario!=EWarSiegeScenario::FullSiege || !StageClaims
        || (State.Phase!=EWarSiegePhase::Active && State.Phase!=EWarSiegePhase::Transition)
        || (State.Phase==EWarSiegePhase::Transition && ((State.Stage==0 && State.MainClaims!=15) || (State.Stage==1 && State.MainClaims!=127) || State.Stage==2))
        || State.ResultCount || State.bAttackersWon || (State.MainClaims&0x80)!=0 || (State.OptionalClaims&~7)!=0
        || State.MilestoneSeconds.Num()!=Claims || !FMath::IsFinite(State.Elapsed) || State.Elapsed<0
        || !FMath::IsFinite(State.Remaining) || State.Remaining<0
        || State.Remaining>(State.Phase==EWarSiegePhase::Transition ? WarSiege::TransitionSeconds : State.bOvertime ? WarSiege::OvertimeSeconds : WarSiege::StageSeconds))
    { Error=TEXT("The baseline left authentic unfinished v2 siege progression.");return false; }
    double PreviousTime=0;
    for (double Time:State.MilestoneSeconds)
    {
        if (!FMath::IsFinite(Time) || Time<=0 || Time<PreviousTime || Time>State.Elapsed)
        { Error=TEXT("The baseline capture milestones do not match the actual siege clock.");return false; }
        PreviousTime=Time;
    }
    if (!bBaselineStarted)
    {
        if (State.Stage || State.MainClaims || State.OptionalClaims || State.Elapsed || State.Phase!=EWarSiegePhase::Active)
        { Error=TEXT("The baseline must start through the ordinary zero-claim stage-zero StartRound.");return false; }
    }
    else
    {
        if (State.Elapsed<BaselinePrevious.Elapsed || (State.MainClaims&BaselinePrevious.MainClaims)!=BaselinePrevious.MainClaims
            || (State.OptionalClaims&BaselinePrevious.OptionalClaims)!=BaselinePrevious.OptionalClaims
            || State.MilestoneSeconds.Num()<BaselinePrevious.MilestoneSeconds.Num())
        { Error=TEXT("The baseline reset or discarded an earned capture milestone.");return false; }
        for (int32 I=0;I<BaselinePrevious.MilestoneSeconds.Num();++I)
            if (State.MilestoneSeconds[I]!=BaselinePrevious.MilestoneSeconds[I])
            { Error=TEXT("An earned baseline capture time changed.");return false; }
        const bool SamePhase=State.Stage==BaselinePrevious.Stage && State.Phase==BaselinePrevious.Phase;
        const bool BeginTransition=State.Stage==BaselinePrevious.Stage && BaselinePrevious.Phase==EWarSiegePhase::Active && State.Phase==EWarSiegePhase::Transition;
        const bool FinishTransition=State.Stage==BaselinePrevious.Stage+1 && BaselinePrevious.Phase==EWarSiegePhase::Transition && State.Phase==EWarSiegePhase::Active;
        if ((!SamePhase && !BeginTransition && !FinishTransition)
            || (FinishTransition && (BaselineTransitionAt[BaselinePrevious.Stage]<0
                || State.Elapsed-BaselineTransitionAt[BaselinePrevious.Stage]<WarSiege::TransitionSeconds-.1)))
        { Error=TEXT("The baseline skipped an earned stage or its real sixty-second transition.");return false; }
    }
    TArray<TSharedPtr<FJsonValue>> Gates;TSet<FString> GateIds;
    if (Encounter->Battlefield->StageGates.Num()!=2)
    { Error=TEXT("The preserved baseline must retain its actual two stage-gate assemblies.");return false; }
    for (int32 StageIndex=0;StageIndex<2;++StageIndex)
    {
        const auto* Gate=Encounter->Battlefield->StageGates[StageIndex].Get();
        if (!IsValid(Gate) || GateIds.Contains(Gate->GetPathName()))
        { Error=TEXT("The baseline gate witness has a missing or duplicate native actor.");return false; }
        GateIds.Add(Gate->GetPathName());
        const bool Hidden=Gate->IsHidden(),Collision=Gate->GetActorEnableCollision(),Open=Hidden && !Collision;
        const bool Expected=(State.MainClaims&(StageIndex==0 ? 0x08 : 0x40))!=0;
        if (Hidden!=Expected || Collision==Expected)
        { Error=TEXT("An actual baseline stage gate disagrees with earned capture ownership.");return false; }
        auto Witness=MakeShared<FJsonObject>();Witness->SetStringField(TEXT("id"),Gate->GetPathName());
        Witness->SetNumberField(TEXT("stageIndex"),StageIndex);Witness->SetBoolField(TEXT("open"),Open);
        Witness->SetBoolField(TEXT("hidden"),Hidden);Witness->SetBoolField(TEXT("collisionEnabled"),Collision);
        TArray<TSharedPtr<FJsonValue>> Components;TInlineComponentArray<UPrimitiveComponent*> Primitives;Gate->GetComponents(Primitives);
        Primitives.Sort([](const UPrimitiveComponent& Left,const UPrimitiveComponent& Right) { return Left.GetPathName()<Right.GetPathName(); });
        for (const auto* Component:Primitives)
        {
            auto Part=MakeShared<FJsonObject>();Part->SetStringField(TEXT("id"),Component->GetPathName());
            Part->SetBoolField(TEXT("collisionEnabled"),Component->IsCollisionEnabled());Part->SetBoolField(TEXT("hiddenInGame"),bool(Component->bHiddenInGame));
            Part->SetBoolField(TEXT("visible"),Component->IsVisible());Components.Add(MakeShared<FJsonValueObject>(Part));
        }
        Witness->SetArrayField(TEXT("components"),Components);Gates.Add(MakeShared<FJsonValueObject>(Witness));
    }
    if (!bBaselineStarted || Force || State.Stage!=BaselinePrevious.Stage || State.Phase!=BaselinePrevious.Phase
        || State.MainClaims!=BaselinePrevious.MainClaims || State.OptionalClaims!=BaselinePrevious.OptionalClaims)
    {
        auto Row=MakeShared<FJsonObject>();SiegeClock(State,Row);
        Row->SetNumberField(TEXT("stage"),State.Stage);Row->SetStringField(TEXT("phase"),SiegePhase(State.Phase));
        Row->SetNumberField(TEXT("elapsedSeconds"),State.Elapsed);Row->SetNumberField(TEXT("resultCount"),State.ResultCount);
        Row->SetBoolField(TEXT("commanderVictory"),State.bAttackersWon);Row->SetArrayField(TEXT("gates"),Gates);
        BaselineObservations.Add(MakeShared<FJsonValueObject>(Row));
        if (State.Phase==EWarSiegePhase::Transition && BaselineTransitionAt[State.Stage]<0) BaselineTransitionAt[State.Stage]=State.Elapsed;
    }
    bBaselineStarted=true;BaselinePrevious=State;return true;
}

TSharedPtr<FJsonObject> UWarCitadelSiegeProof::BaselineProgression() const
{
    auto Record=MakeShared<FJsonObject>();Record->SetNumberField(TEXT("version"),1);
    const TSharedPtr<FJsonObject> Initial=BaselineObservations.IsEmpty() ? nullptr : BaselineObservations[0]->AsObject();
    Record->SetNumberField(TEXT("startedStage"),Initial ? Initial->GetNumberField(TEXT("stage")) : -1);
    Record->SetNumberField(TEXT("startedMainClaims"),Initial ? Initial->GetNumberField(TEXT("mainClaims")) : -1);
    Record->SetNumberField(TEXT("startedOptionalClaims"),Initial ? Initial->GetNumberField(TEXT("optionalClaims")) : -1);
    Record->SetArrayField(TEXT("observations"),BaselineObservations);
    Record->SetNumberField(TEXT("settledStage"),bBaselineSettled ? BaselinePrevious.Stage : -1);
    Record->SetNumberField(TEXT("settledMainClaims"),bBaselineSettled ? BaselinePrevious.MainClaims : -1);
    Record->SetBoolField(TEXT("commanderVictory"),BaselinePrevious.bAttackersWon);return Record;
}

bool UWarCitadelSiegeProof::BenchmarkGoal(int32 Slot,FVector& Goal) const
{
    if (!bPerformance || Round!=1 || !Encounter || Encounter->bPreparing || Encounter->bLeasePaused
        || Encounter->Siege.Phase!=EWarSiegePhase::Active || !PerformanceCameras.IsValidIndex(Encounter->Siege.Stage)
        || PerformanceWindows[Encounter->Siege.Stage]->AsObject()->GetNumberField(TEXT("endElapsedSeconds"))
            -PerformanceWindows[Encounter->Siege.Stage]->AsObject()->GetNumberField(TEXT("startElapsedSeconds"))>=60) return false;
    const auto PositionsForStage=PerformanceCameras[Encounter->Siege.Stage]->AsObject()->GetArrayField(TEXT("positions"));
    if (!PositionsForStage.IsValidIndex(Slot)) return false;
    const auto Values=PositionsForStage[Slot]->AsArray();
    if (Values.Num()!=3) return false;
    Goal=FVector(Values[0]->AsNumber(),Values[1]->AsNumber(),Values[2]->AsNumber());return !Goal.ContainsNaN();
}

void UWarCitadelSiegeProof::SamplePerformance()
{
    if (!bPerformance || !PerformanceWriter || Round!=1 || !Encounter || !Encounter->Battlefield) return;
    const auto* ActualCity=Encounter->Battlefield->CityDefinition.Get();
    if (!ActualCity || ActualCity->Revision!=Revision || (bPerformanceBaseline && ActualCity->GetOutermost()->GetName()!=PreservedCity))
    { Finish(false,TEXT("The rendered battlefield changed its actual bound city definition."));return; }
    const double Wall=FPlatformTime::Seconds(),FrameMs=(Wall-PerformancePrevious)*1000;
    const bool Active=Encounter->Siege.Phase==EWarSiegePhase::Active && !Encounter->bPreparing && !Encounter->bLeasePaused;
    const int32 Stage=Encounter->Siege.Stage;
    auto* Observer=GetWorld()->GetFirstPlayerController();
    if (!Observer || !PerformanceCameras.IsValidIndex(Stage)) return;
    const auto CameraConfig=PerformanceCameras[Stage]->AsObject();
    if (Active && PerformanceStage!=Stage)
    {
        if (!PerformanceSourceCity)
        {
            PerformanceSourceCity=MakeShared<FJsonObject>();
            PerformanceSourceCity->SetStringField(TEXT("path"),Encounter->Battlefield->CityDefinition->GetOutermost()->GetName());
            PerformanceSourceCity->SetStringField(TEXT("assetPath"),Encounter->Battlefield->CityDefinition->GetPathName());
            PerformanceSourceCity->SetStringField(TEXT("revision"),Encounter->Battlefield->CityDefinition->Revision);
        }
        FVector Eye,Target;ReadPoint(CameraConfig,TEXT("eye"),Eye);ReadPoint(CameraConfig,TEXT("target"),Target);
        const int32 First=Stage==0 ? 0 : Stage==1 ? 4 : 7,Last=Stage==0 ? 3 : Stage==1 ? 6 : 7;
        AWarCharacter* NavigationAvatar=nullptr;
        for (TActorIterator<AWarCharacter> It(GetWorld());It;++It)
            if (Encounter->IsParticipant(*It) && !It->IsDead()) { NavigationAvatar=*It;break; }
        if (!NavigationAvatar) return;
        const auto PositionsForStage=CameraConfig->GetArrayField(TEXT("positions"));
        for (int32 Slot=0;Slot<PositionsForStage.Num();++Slot)
        {
            const auto Values=PositionsForStage[Slot]->AsArray();
            if (Values.Num()!=3) { bPerformanceWriteFailed=true;return; }
            const FVector Feet(Values[0]->AsNumber(),Values[1]->AsNumber(),Values[2]->AsNumber());
            FHitResult Floor;FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelBenchmark),false);
            // Moving participants do not become floor/headroom geometry. Ordinary
            // CharacterMovement still resolves their actual crowd collisions.
            for (TActorIterator<APawn> PawnIt(GetWorld());PawnIt;++PawnIt) Query.AddIgnoredActor(*PawnIt);
            const auto* Capsule=GetDefault<AWarCharacter>()->GetCapsuleComponent();
            const float Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
            const bool HasFloor=!Feet.ContainsNaN() && GetWorld()->LineTraceSingleByObjectType(Floor,Feet+FVector(0,0,100),Feet-FVector(0,0,100),
                FCollisionObjectQueryParams(ECC_WorldStatic),Query) && Floor.ImpactNormal.Z>=NavigationAvatar->GetCharacterMovement()->GetWalkableFloorZ()
                && FMath::Abs(Floor.ImpactPoint.Z-Feet.Z)<=25;
            const FVector Center=HasFloor ? Floor.ImpactPoint+FVector(0,0,Half-Radius+Radius/Floor.ImpactNormal.Z+3) : Feet;
            const bool Clear=HasFloor && !GetWorld()->OverlapBlockingTestByChannel(Center,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(Radius,Half),Query);
            auto PositionEvidence=MakeShared<FJsonObject>();PositionEvidence->SetNumberField(TEXT("stage"),Stage);PositionEvidence->SetNumberField(TEXT("index"),Slot);
            PositionEvidence->SetArrayField(TEXT("point"),JsonPoint(Feet));PositionEvidence->SetArrayField(TEXT("actualFloor"),JsonPoint(Floor.ImpactPoint));
            PositionEvidence->SetNumberField(TEXT("floorNormalZ"),Floor.ImpactNormal.Z);PositionEvidence->SetBoolField(TEXT("floorClear"),HasFloor);
            PositionEvidence->SetBoolField(TEXT("capsuleClear"),Clear);PositionEvidence->SetNumberField(TEXT("capsuleRadiusCm"),Radius);
            PositionEvidence->SetNumberField(TEXT("capsuleHalfHeightCm"),Half);
            double MinimumCaptureDistance=FVector::Dist2D(Feet,Encounter->Battlefield->OptionalObjectives[Stage]);
            for (int32 I=First;I<=Last;++I)
                MinimumCaptureDistance=FMath::Min(MinimumCaptureDistance,FVector::Dist2D(Feet,Encounter->Battlefield->Objectives[I]));
            const bool CaptureExclusion=MinimumCaptureDistance>=Encounter->Battlefield->ObjectiveRadius+50;
            PositionEvidence->SetBoolField(TEXT("captureExclusion"),CaptureExclusion);
            PositionEvidence->SetNumberField(TEXT("minimumCaptureDistanceCm"),MinimumCaptureDistance);
            PositionEvidence->SetNumberField(TEXT("captureRadiusCm"),Encounter->Battlefield->ObjectiveRadius);
            const FVector Entry=Encounter->Battlefield->TeamSpawns[Stage*2+(Slot<18 ? 0 : 1)];
            const auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(),Entry,Feet,NavigationAvatar);
            const bool Reachable=Path && Path->IsValid() && !Path->IsPartial();PositionEvidence->SetBoolField(TEXT("navigation"),Reachable);
            PerformancePositions.Add(MakeShared<FJsonValueObject>(PositionEvidence));
            bPerformanceWriteFailed|=!HasFloor || !Clear || !Reachable || !CaptureExclusion;
        }
        if (bPerformanceWriteFailed) { Finish(false,TEXT("A signed performance formation has a blocked floor, capsule, route or capture exclusion."));return; }
        if (!PerformanceCamera) PerformanceCamera=GetWorld()->SpawnActor<ACameraActor>();
        if (!PerformanceCamera) { Finish(false,TEXT("Cannot create the native performance observation camera."));return; }
        PerformanceCamera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());
        PerformanceCamera->GetCameraComponent()->SetFieldOfView(CameraConfig->GetNumberField(TEXT("fieldOfView")));
        Observer->bAutoManageActiveCameraTarget=false;Observer->SetViewTarget(PerformanceCamera);
        PerformanceStage=Stage;PerformanceStageBegan=Wall;PerformanceRunStart=-1;PerformanceRunSeconds=0;PerformanceRunFrames=0;return;
    }
    const auto* CameraManager=Observer->PlayerCameraManager.Get();
    const FVector ActualEye=CameraManager ? CameraManager->GetCameraLocation() : FVector::ZeroVector;
    const FVector ActualDirection=CameraManager ? CameraManager->GetCameraRotation().Vector() : FVector::ZeroVector;
    const float ActualFov=CameraManager ? CameraManager->GetFOVAngle() : 0;
    FVector SignedEye,SignedLook;ReadPoint(CameraConfig,TEXT("eye"),SignedEye);ReadPoint(CameraConfig,TEXT("target"),SignedLook);
    const bool CameraMatches=CameraManager && PerformanceCamera && Observer->GetViewTarget()==PerformanceCamera
        && ActualEye.Equals(SignedEye,1) && ActualDirection.Equals((SignedLook-SignedEye).GetSafeNormal(),.0001)
        && FMath::Abs(ActualFov-CameraConfig->GetNumberField(TEXT("fieldOfView")))<=.01;
    int32 Enrolled[2]={},Alive=0,Dead=0,Respawning=0,Avatars=0,ModelReady=0,Visible=0,Normalized=0;
    int32 Projected=0,RecentlyRendered=0,Unoccluded=0;
    TArray<TSharedPtr<FJsonValue>> Roster;TArray<FString> RosterKeys;
    const FIntPoint Viewport=GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport
        ? GEngine->GameViewport->Viewport->GetSizeXY() : FIntPoint::ZeroValue;
    for (TActorIterator<AController> It(GetWorld());It;++It)
    {
        const auto* PS=It->GetPlayerState<AWarPlayerState>();
        if (!PS || !Encounter->Owns(PS) || PS->GetSiegeUnit()!=EWarSiegeUnit::Participant) continue;
        const int32 Team=PS->GetRealm()==EWarRealm::Aegis ? 0 : PS->GetRealm()==EWarRealm::Riftbound ? 1 : -1;
        if (Team<0) continue;++Enrolled[Team];Normalized+=PS->IsSiegeNormalized();
        const auto* Pawn=Cast<AWarCharacter>(It->GetPawn());
        if (!Pawn) { ++Respawning;continue; }++Avatars;
        if (Pawn->IsDead()) ++Dead;else ++Alive;
        const auto* Mesh=Pawn->GetMesh();
        if (!Pawn->IsVisualReady() || !Mesh || !Mesh->GetSkeletalMeshAsset() || Pawn->IsHidden() || !Mesh->IsVisible()) continue;
        const auto* Visual=Pawn->GetVisualDefinition();if (!Visual) continue;
        ++ModelReady;FVector2D Screen;
        const bool Recent=Mesh->GetLastRenderTimeOnScreen()>0 && GetWorld()->GetTimeSeconds()-Mesh->GetLastRenderTimeOnScreen()<=.1;
        const bool Onscreen=UGameplayStatics::ProjectWorldToScreen(Observer,Mesh->Bounds.Origin,Screen)
            && Screen.X>=0 && Screen.Y>=0 && Screen.X<Viewport.X && Screen.Y<Viewport.Y;
        FHitResult Occlusion;FCollisionQueryParams SightQuery(SCENE_QUERY_STAT(CitadelCrowdVisibility),false,Pawn);
        if (Observer->GetPawn()) SightQuery.AddIgnoredActor(Observer->GetPawn());
        const bool ClearSight=CameraManager && !GetWorld()->LineTraceSingleByChannel(Occlusion,ActualEye,Mesh->Bounds.Origin,ECC_Visibility,SightQuery);
        Projected+=Onscreen;RecentlyRendered+=Recent;Unoccluded+=ClearSight;
        if (Recent && Onscreen && ClearSight) ++Visible;
        TArray<FString> EquipmentRows;
        for (const auto& Reference:PS->GetInventory().Equipment)
            if (const auto* Item=PS->GetInventory().Items.FindByPredicate([&](const auto& Candidate) { return Candidate.Slot==Reference.BagSlot; }))
                EquipmentRows.Add(FString::Printf(TEXT("%s:%s:%s:%d:%d"),*Reference.Slot.ToString(),*Item->Key.ToString(),*Item->Kind.ToString(),Item->bHasAffix,Item->StrengthBonus));
        EquipmentRows.Sort();
        const FString Equipment=FString::Join(EquipmentRows,TEXT("|"))+TEXT("|")+Visual->WeaponMesh.ToSoftObjectPath().ToString()
            +TEXT("|")+Visual->ShieldMesh.ToSoftObjectPath().ToString()+TEXT("|")+Visual->SourceSha256;
        auto Member=MakeShared<FJsonObject>();Member->SetStringField(TEXT("realm"),Team==0 ? TEXT("aegis") : TEXT("riftbound"));
        Member->SetStringField(TEXT("careerId"),Pawn->GetCareerId().ToString());Member->SetStringField(TEXT("visualAsset"),Visual->GetPathName());
        Member->SetNumberField(TEXT("combatLevel"),PS->GetCombatLevel());
        Member->SetStringField(TEXT("equipmentSignature"),TextHash(Equipment));
        FString Canonical;FJsonSerializer::Serialize(Member,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Canonical));
        RosterKeys.Add(Canonical);Roster.Add(MakeShared<FJsonValueObject>(Member));
    }
    RosterKeys.Sort();const FString RosterCanonical=FString::Join(RosterKeys,TEXT("\n")),RosterHash=TextHash(RosterCanonical);
    const FString StatsMode=Normalized==36 ? TEXT("normalized") : Normalized==0 ? TEXT("normal") : TEXT("mixed");
    if (Roster.Num()==36 && PerformanceRoster.IsEmpty())
    { PerformanceRoster=Roster;PerformanceRosterHash=RosterHash;PerformanceRosterCanonical=RosterCanonical;PerformanceStatsMode=StatsMode; }
    const auto Settings=PerformanceSettings();
    const int32 Streaming=IStreamingManager::Get().GetNumWantingResources();
    const double GameMs=FPlatformTime::ToMilliseconds(GGameThreadTime),RenderMs=FPlatformTime::ToMilliseconds(GRenderThreadTime);
    const double RhiMs=FPlatformTime::ToMilliseconds(GRHIThreadTime),GpuMs=FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles());
    const bool Settled=Wall-PerformanceStageBegan>=10;
    const bool Eligible=Active && Settled && CameraMatches && PerformanceSettingsValid(Settings) && Enrolled[0]==18 && Enrolled[1]==18
        && Avatars==36 && ModelReady==36 && Visible==36 && Streaming==0 && FrameMs>0 && GameMs>0 && RenderMs>0 && GpuMs>0
        && RosterHash==PerformanceRosterHash && StatsMode==PerformanceStatsMode;
    auto Row=MakeShared<FJsonObject>();
    Row->SetNumberField(TEXT("stage"),Stage);Row->SetNumberField(TEXT("index"),PerformanceFrames);
    Row->SetNumberField(TEXT("elapsedSeconds"),Wall-PerformanceBegan);Row->SetNumberField(TEXT("stageElapsedSeconds"),Wall-PerformanceStageBegan);
    Row->SetBoolField(TEXT("settled"),Settled);Row->SetBoolField(TEXT("eligible"),Eligible);Row->SetObjectField(TEXT("settings"),Settings);
    Row->SetBoolField(TEXT("encounterActive"),Active);Row->SetBoolField(TEXT("leasePaused"),Encounter->bLeasePaused);Row->SetBoolField(TEXT("preparing"),Encounter->bPreparing);
    Row->SetStringField(TEXT("phase"),SiegePhase(Encounter->Siege.Phase));
    if (bPerformanceBaseline) SiegeClock(Encounter->Siege,Row);
    FVector BenchmarkPoint;Row->SetBoolField(TEXT("benchmarkOrders"),BenchmarkGoal(0,BenchmarkPoint));
    Row->SetNumberField(TEXT("frameMs"),FrameMs);Row->SetNumberField(TEXT("gameThreadMs"),GameMs);Row->SetNumberField(TEXT("renderThreadMs"),RenderMs);
    Row->SetNumberField(TEXT("rhiThreadMs"),RhiMs);Row->SetNumberField(TEXT("gpuMs"),GpuMs);
    Row->SetNumberField(TEXT("drawCalls"),GNumDrawCallsRHI[0]);Row->SetNumberField(TEXT("primitives"),GNumPrimitivesDrawnRHI[0]);
    Row->SetNumberField(TEXT("physicalMiB"),FPlatformMemory::GetStats().UsedPhysical/1048576.);
    Row->SetNumberField(TEXT("aegisEnrolled"),Enrolled[0]);Row->SetNumberField(TEXT("riftboundEnrolled"),Enrolled[1]);
    Row->SetNumberField(TEXT("alive"),Alive);Row->SetNumberField(TEXT("dead"),Dead);Row->SetNumberField(TEXT("respawning"),Respawning);
    Row->SetNumberField(TEXT("avatars"),Avatars);Row->SetNumberField(TEXT("modelReady"),ModelReady);Row->SetNumberField(TEXT("visible"),Visible);
    Row->SetNumberField(TEXT("projected"),Projected);Row->SetNumberField(TEXT("recentlyRendered"),RecentlyRendered);Row->SetNumberField(TEXT("unoccluded"),Unoccluded);
    Row->SetStringField(TEXT("rosterSha256"),RosterHash);Row->SetStringField(TEXT("statsMode"),StatsMode);
    Row->SetNumberField(TEXT("streamingRequests"),Streaming);
    Row->SetBoolField(TEXT("cameraMatches"),CameraMatches);
    Row->SetArrayField(TEXT("cameraEye"),JsonPoint(ActualEye));Row->SetArrayField(TEXT("cameraDirection"),JsonPoint(ActualDirection));
    Row->SetNumberField(TEXT("cameraFov"),ActualFov);
    FString Json;FJsonSerializer::Serialize(Row,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
    if (PerformanceFrames) Json=TEXT(",")+Json;const FTCHARToUTF8 Utf8(*Json);
    PerformanceWriter->Serialize(const_cast<ANSICHAR*>(Utf8.Get()),Utf8.Length());++PerformanceFrames;
    PerformancePrevious=Wall;
    bPerformanceWriteFailed|=PerformanceWriter->IsError();
    if (!Eligible) { PerformanceRunStart=-1;PerformanceRunSeconds=0;PerformanceRunFrames=0;return; }
    if (PerformanceRunStart<0) PerformanceRunStart=Wall-PerformanceBegan;
    ++PerformanceRunFrames;PerformanceRunSeconds=Wall-PerformanceBegan-PerformanceRunStart;
    const auto Window=PerformanceWindows[Stage]->AsObject();
    if (PerformanceRunSeconds>Window->GetNumberField(TEXT("endElapsedSeconds"))-Window->GetNumberField(TEXT("startElapsedSeconds")))
    {
        Window->SetNumberField(TEXT("startElapsedSeconds"),PerformanceRunStart);Window->SetNumberField(TEXT("endElapsedSeconds"),Wall-PerformanceBegan);
        Window->SetNumberField(TEXT("frameCount"),PerformanceRunFrames);
    }
}

bool UWarCitadelSiegeProof::FinishPerformance(bool GameplayPassed,FString& Error)
{
    if (!bPerformance) return true;
    bool Complete=PerformanceWriter && !bPerformanceWriteFailed;
    if (PerformanceWriter)
    {
        const FTCHARToUTF8 Suffix(TEXT("],\"complete\":true}"));
        PerformanceWriter->Serialize(const_cast<ANSICHAR*>(Suffix.Get()),Suffix.Length());PerformanceWriter->Flush();
        Complete&=!PerformanceWriter->IsError() && PerformanceWriter->Close();PerformanceWriter.Reset();
    }
    Complete&=CheckPerformanceBindings(Error) && PerformanceSettingsValid(PerformanceSettings());
    for (const auto& Value:PerformanceWindows)
    {
        const auto Window=Value->AsObject();
        Complete&=Window->GetNumberField(TEXT("endElapsedSeconds"))-Window->GetNumberField(TEXT("startElapsedSeconds"))>=60;
    }
    Complete&=PerformanceWindows.Num()==3 && GameplayPassed && PerformancePositions.Num()==108 && PerformanceRoster.Num()==36
        && (!bPerformanceBaseline || bBaselineSettled);
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("schemaVersion"),1);
    Report->SetBoolField(TEXT("performanceOnly"),true);Report->SetBoolField(TEXT("proofOnly"),true);Report->SetBoolField(TEXT("passed"),Complete);
    Report->SetBoolField(TEXT("performanceBaseline"),bPerformanceBaseline);Report->SetBoolField(TEXT("isolatedStageWindows"),false);
    if (bPerformanceBaseline)
    {
        Report->SetStringField(TEXT("fixtureMode"),BaselineFixtureMode);
        Report->SetBoolField(TEXT("earnedProgressionObserved"),bBaselineSettled);
        Report->SetObjectField(TEXT("baselineProgression"),BaselineProgression());
    }
    Report->SetStringField(TEXT("map"),Map);Report->SetStringField(TEXT("mapSha256"),MapHash);
    Report->SetStringField(TEXT("cityRevision"),Revision);Report->SetStringField(TEXT("signature"),Signature);
    Report->SetStringField(TEXT("configSha256"),PerformanceConfigHash);
    if (PerformanceBindings) Report->SetObjectField(TEXT("bindings"),PerformanceBindings);
    if (PerformanceHardware) Report->SetObjectField(TEXT("hardware"),PerformanceHardware);
    Report->SetObjectField(TEXT("settings"),PerformanceSettings());Report->SetArrayField(TEXT("windows"),PerformanceWindows);
    Report->SetArrayField(TEXT("roster"),PerformanceRoster);Report->SetStringField(TEXT("rosterSha256"),PerformanceRosterHash);
    Report->SetStringField(TEXT("rosterCanonical"),PerformanceRosterCanonical);
    Report->SetStringField(TEXT("statsMode"),PerformanceStatsMode);
    Report->SetArrayField(TEXT("formationPositions"),PerformancePositions);
    if (PerformanceSourceCity) Report->SetObjectField(TEXT("sourceCity"),PerformanceSourceCity);
    if (PerformanceBaselineManifest)
    {
        Report->SetObjectField(TEXT("baselinePackageHashes"),PerformanceBaselineManifest->GetObjectField(TEXT("packageHashes")));
        Report->SetObjectField(TEXT("baselineSourceHashes"),PerformanceBlueprint->GetObjectField(TEXT("sourceHashes")));
        Report->SetObjectField(TEXT("baselineDependencyHashes"),PerformanceBlueprint->GetObjectField(TEXT("dependencyHashes")));
    }
    auto Frames=MakeShared<FJsonObject>();Frames->SetStringField(TEXT("path"),PerformanceFramesPath);
    Frames->SetStringField(TEXT("sha256"),FileHash(PerformanceFramesPath));Frames->SetNumberField(TEXT("count"),PerformanceFrames);
    Report->SetObjectField(TEXT("frames"),Frames);
    Report->SetStringField(TEXT("timingSource"),TEXT("FPlatformTime wall interval; stock previous-frame GGameThreadTime/GRenderThreadTime/GRHIThreadTime/RHIGetGPUFrameCycles"));
    Report->SetStringField(TEXT("scope"),TEXT("Local editor-hosted standalone synthetic 18v18; reference hardware, platforms and real network load unverified"));
    for (const TCHAR* Flag:{TEXT("productionAdmission"),TEXT("steamAdmission"),TEXT("humanPlaytest"),TEXT("visualApproval"),TEXT("releaseAcceptance"),TEXT("referenceHardwareCertified"),
        TEXT("progressionAcceptance"),TEXT("victoryAcceptance"),TEXT("conquestAcceptance"),TEXT("routeAcceptance"),TEXT("fullSiegeAdmission")})
        Report->SetBoolField(Flag,false);
    if (!Complete && Error.IsEmpty()) Error=TEXT("Actual rendered crowd exposure did not complete three uninterrupted settled 60-second 18v18 windows.");
    Report->SetStringField(TEXT("detail"),Complete ? TEXT("Actual uncapped crowd exposure collected; evaluate frame budget independently from raw frames.") : Error);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    if (!FFileHelper::SaveStringToFile(Json,*(FPaths::GetPath(ConfigPath)/TEXT("performance-report.json"))))
    { Error=TEXT("Could not save native performance evidence.");return false; }
    return Complete;
}
bool UWarCitadelSiegeProof::Start(FString& Error)
{
    AWarSiegeBattlefield* Field = nullptr;
    for (TActorIterator<AWarSiegeBattlefield> It(GetWorld()); It; ++It)
    { if (Field) { Error = TEXT("Duplicate siege overlays in the proof world."); return false; } Field = *It; }
    if (!Field || !Field->CityDefinition)
    { Error=TEXT("The candidate battlefield or shared city definition is not loaded.");return false; }
    if (Field->DefinitionVersion != 2 || Field->CityDefinition->Revision != Revision)
    { Error = TEXT("The authored overlay belongs to another rules or scenery revision."); return false; }
    if (bPerformanceBaseline && Field->CityDefinition->GetOutermost()->GetName()!=PreservedCity)
    { Error=TEXT("The benchmark must render the actual preserved published city definition, without a private substitute.");return false; }
    if (bPerformanceBaseline && !PerformanceBaselineManifest->GetObjectField(TEXT("packageHashes"))->HasField(Field->GetOutermost()->GetName()))
    { Error=TEXT("The actual baseline battlefield overlay is missing its saved package hash.");return false; }
    if (bPerformance)
    {
        const TArray<TSharedPtr<FJsonValue>>* Anchors=nullptr;const TArray<TSharedPtr<FJsonValue>>* Spawns=nullptr;
        const TArray<TSharedPtr<FJsonValue>>* Optionals=nullptr;
        if (!PerformanceBlueprint || !PerformanceBlueprint->TryGetArrayField(TEXT("objectives"),Anchors) || Anchors->Num()!=8
            || !PerformanceBlueprint->TryGetArrayField(TEXT("optionalObjectives"),Optionals) || Optionals->Num()!=3
            || !PerformanceBlueprint->TryGetArrayField(TEXT("teamSpawns"),Spawns) || Spawns->Num()!=6)
        { Error=TEXT("The signed benchmark source does not contain the full native stage anchors and spawns.");return false; }
        for (int32 I=0;I<8;++I)
        {
            FVector Point;
            if (!ReadPointValue((*Anchors)[I],Point) || !Field->Objectives.IsValidIndex(I) || !Field->Objectives[I].Equals(Point,1))
            { Error=TEXT("An actual native objective differs from the signed benchmark source.");return false; }
        }
        for (int32 I=0;I<3;++I)
        {
            FVector Point;
            if (!ReadPointValue((*Optionals)[I],Point) || !Field->OptionalObjectives.IsValidIndex(I) || !Field->OptionalObjectives[I].Equals(Point,1))
            { Error=TEXT("An actual optional objective differs from the signed benchmark source.");return false; }
        }
        for (int32 I=0;I<6;++I)
        {
            FVector Point;
            if (!ReadPointValue((*Spawns)[I],Point) || !Field->TeamSpawns.IsValidIndex(I) || !Field->TeamSpawns[I].Equals(Point,1))
            { Error=TEXT("An actual native spawn differs from the signed benchmark source.");return false; }
        }
    }
    // This explicitly disclosed, in-memory fixture bypass cannot survive process exit.
    // Every native model, class-role, ability, convoy, navigation and prop check still runs.
    if (bFixtureReview)
    { Field->ReviewedCityRevision = Revision; Field->bTraversalReviewed = true; Field->bEquippedRosterReviewed = true; }
    if (bLive)
    {
        const auto* Streaming=GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
        if (!Streaming || !Streaming->IsZoneReady(TEXT("aegis_capital"),nullptr,&Error))
        { Error=TEXT("Capital streaming readiness: ")+Error;return false; }
    }
    if (!Field->Validate(Error,EWarSiegeScenario::FullSiege,bLive)) return false;
    if (bLive)
    {
        Encounter = AWarSiegeEncounter::Capital(GetWorld());
        if (!Encounter) return false; // The real owning-host bridge performs activation.
        if (Encounter->ContentRevision != Revision) { Error = TEXT("The trusted activation is for another city."); return false; }
        if (!SpawnLivePlayers(Field,Error)) return false;
        bLivePreparationObserved|=Encounter->bPreparing;
        bLiveServicesSuspendedObserved|=Encounter->SuspendsServices(TEXT("aegis_capital"));
        if (Encounter->bPreparing || Encounter->bLeasePaused) return false;
        Round = 1; return true;
    }
    if (!Sentinel)
    {
        const auto* Entry = Field->Roster.FindByPredicate([](const auto& Row) { return Row.Realm == EWarRealm::Aegis; });
        auto* Visual = Entry ? Entry->Visual.LoadSynchronous() : nullptr;
        FVector Center;
        if (!Visual || !WarSiegeNavigation::SpawnCenter(GetWorld(),Field->TeamSpawns[0],Center))
        { Error = TEXT("The unrelated normal-avatar sentinel has no approved model or clear floor."); return false; }
        auto* Controller = GetWorld()->SpawnActor<AWarSiegeBotController>();
        auto* PS = Controller ? Controller->GetPlayerState<AWarPlayerState>() : nullptr;
        if (!PS) { Error = TEXT("Cannot initialize the unrelated normal PlayerState."); return false; }
        PS->SetDevelopmentRealm(EWarRealm::Aegis); Controller->SetActorTickEnabled(false);
        const FTransform Transform(FRotator::ZeroRotator,Center);
        Sentinel = GetWorld()->SpawnActorDeferred<AWarCharacter>(AWarCharacter::StaticClass(),Transform,Controller,
            nullptr,ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding);
        if (!Sentinel || !Sentinel->SetVisualDefinition(Visual,Error)) return false;
        Sentinel->FinishSpawning(Transform); Controller->Possess(Sentinel);
        PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),100);
        PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxManaAttribute(),100);
        PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),73);
        PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),61);
    }
    Encounter = AWarSiegeEncounter::Find(GetWorld());
    if (!Encounter) Encounter = GetWorld()->SpawnActor<AWarSiegeEncounter>();
    if (!Encounter || !Encounter->StartRound(18, 58182 + Round, EWarSiegeScenario::FullSiege, Error)) return false;
    // The preserved-city benchmark uses this same ordinary zero-claim launch.
    // Its later gate openings must be earned by capture and convoy movement.
    if (!ObserveBaselineProgression(Error)) return false;
    ++Round;
    if (DiagnosticSeconds>0 && DiagnosticStartedAt<0) DiagnosticStartedAt=GetWorld()->GetTimeSeconds();
    return true;
}
bool UWarCitadelSiegeProof::SpawnLivePlayers(AWarSiegeBattlefield* Field,FString& Error)
{
    auto* Bridge=GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>(); if (!Bridge) return false;
    for (int32 I=0;I<LiveIds.Num();++I)
    {
        auto* PC=LivePlayers[I].Get(); const EWarRealm Realm=I<18 ? EWarRealm::Aegis : EWarRealm::Riftbound;
        if (!PC)
        {
            const EWarSiegeRole Role=EWarSiegeRole(I%3);
            const auto* Row=Field->Roster.FindByPredicate([&](const auto& Entry) { return Entry.Realm==Realm && Entry.CombatRole==Role; });
            auto* Visual=Row ? Row->Visual.LoadSynchronous() : nullptr; FVector Center;
            if (!Visual || !WarSiegeNavigation::SpawnCenter(GetWorld(),Field->TeamSpawns[I<18 ? 0 : 1],Center)) return false;
            PC=GetWorld()->SpawnActor<AWarPlayerController>(); if (!PC) return false;
            auto* PS=PC->GetPlayerState<AWarPlayerState>();
            if (!PS) { PS=GetWorld()->SpawnActor<AWarPlayerState>(); PC->PlayerState=PS; PS->SetOwner(PC); }
            PC->ScenarioCharacterId=LiveIds[I]; PC->bCampaignIdentityProvisioned=true;
            PS->SetDevelopmentRealm(Realm); PS->SetPlayerName(LiveIds[I]); PS->SetCurrentZoneTrusted(TEXT("aegis_capital"));
            if (!PS->SetGmLevelTrusted(40,Error)) return false; // Real normal progression, captured before enrollment.
            PC->BeginCharacterEntry(Visual); const FTransform Transform(FRotator::ZeroRotator,Center);
            auto* Pawn=GetWorld()->SpawnActorDeferred<AWarCharacter>(AWarCharacter::StaticClass(),Transform,PC,nullptr,
                ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding);
            if (!Pawn || !Pawn->SetVisualDefinition(Visual,Error)) return false;
            Pawn->FinishSpawning(Transform); PC->Possess(Pawn); PC->CompleteCharacterEntry(); LivePlayers[I]=PC;
        }
        auto* PS=PC->GetPlayerState<AWarPlayerState>();
        if (!PS || PS->IsSiegeNormalized() || PS->GetCombatLevel()!=40)
        { Error=TEXT("A synthetic live character lost its ordinary progression or was normalized."); return false; }
        if (!LiveInitialInventories.Contains(PC->ScenarioCharacterId))
        {
            FString Inventory;
            if (!FJsonObjectConverter::UStructToJsonObjectString(PS->GetInventory(),Inventory))
            { Error=TEXT("The real normal character baseline inventory cannot be recorded.");return false; }
            LiveInitialInventories.Add(PC->ScenarioCharacterId,Inventory);
        }
        if (const auto* Pawn=Cast<AWarCharacter>(PC->GetPawn());PS->IsScenarioTransferPending() && Pawn)
            bLiveCustodyHeldObserved|=Pawn->GetCharacterMovement()->MovementMode==MOVE_None;
        if (!PS->IsSiegeMember() && !PS->IsScenarioTransferPending()) Bridge->Enroll(PC,true);
    }
    return true;
}
void UWarCitadelSiegeProof::DriveLivePlayers()
{
    if (!Encounter || Encounter->Siege.Phase!=EWarSiegePhase::Active || !Encounter->Battlefield) return;
    const auto* Catalog=GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>(); int32 Counts[2]={};
    const bool Update=GetWorld()->GetTimeSeconds()>=NextDrive;
    if (Update) NextDrive=GetWorld()->GetTimeSeconds()+.25;
    for (int32 I=0;I<LivePlayers.Num();++I)
    {
        auto* PC=LivePlayers[I].Get(); auto* PS=PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
        auto* Pawn=PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
        if (!PS || !Pawn || !Encounter->IsParticipant(Pawn) || Pawn->IsDead() || !Pawn->IsVisualReady() || PS->IsScenarioTransferPending()) continue;
        if (PS->IsSiegeNormalized() || PS->GetCombatLevel()!=40) { Finish(false,TEXT("Live combat replaced ordinary stats with scenario normalization.")); return; }
        const bool Attacker=I>=18; ++Counts[Attacker ? 1 : 0];
        if (const auto* Previous=Positions.Find(Pawn)) Movement+=FVector::Dist2D(Pawn->GetActorLocation(),*Previous);
        Positions.Add(Pawn,Pawn->GetActorLocation()); auto* Runtime=PS->GetClassAbilities();
        if (Update)
        {
            // The defense fixture first approaches normally, then disengages. Rules alone consume the stage clock.
            const bool OpeningDefense=bLiveDefended && Encounter->Siege.Elapsed<20;
            FVector Goal=bLiveDefended ? (OpeningDefense ? Encounter->TaskLocation() : Encounter->Battlefield->TeamSpawns[Attacker ? 1 : 0])
                : (Attacker ? Encounter->TaskLocation(I&1) : Encounter->Battlefield->TeamSpawns[Encounter->Siege.Stage*2]);
            const bool CenterProbe=Attacker && I<20 && !bLiveDefended && !bPerformance && !bLockedCenterPhysical
                && Encounter->Siege.Stage==1 && !WarSiege::CenterUnlocked(Encounter->Siege);
            if (CenterProbe) Goal=Encounter->Battlefield->Objective(1,2);
            const bool Benchmark=BenchmarkGoal(I,Goal);
            const bool Escort=Attacker && !bLiveDefended && !Benchmark && Encounter->Siege.Stage==0
                && Encounter->Siege.Objective>0 && Encounter->Convoy.Num()==2;
            const bool ClearVehicle=Escort && !WarSiegeNavigation::ConvoyPositionClear(Pawn,Encounter);
            const bool KeepEscort=Escort && ((I-18)%3==0 || ClearVehicle);
            if (ClearVehicle && Runtime->IsStationaryCast()) Runtime->UpdateMovementIntent(true);
            if (Runtime->IsStationaryCast() || Runtime->OwnsMovement()) { Waypoints.Remove(Pawn);continue; }
            AWarCharacter* Enemy=nullptr; double Distance=FMath::Square(2500.);
            if (Attacker && !Benchmark && (!bLiveDefended || OpeningDefense)) for (TActorIterator<AWarCharacter> Other(GetWorld());Other;++Other)
            {
                const double D=FVector::DistSquared(Pawn->GetActorLocation(),Other->GetActorLocation());
                if (D<Distance && WarCitadelProofTactics::CanTarget(Encounter,Pawn,*Other,2500))
                { Distance=D; Enemy=*Other; }
            }
            if (Enemy && !KeepEscort && !CenterProbe) Goal=Enemy->GetActorLocation(); FVector Ground;
            const bool Formation=Escort && (KeepEscort || !Enemy);
            const float Angle=I*2.399963f;FVector Offset(FMath::Cos(Angle)*360,FMath::Sin(Angle)*360,0);
            if (Formation) Offset=WarSiegeEscort::Offset(I-18,Encounter->Convoy[0]->GetActorRotation().Yaw);
            else if (Escort && Enemy) Offset=(Enemy->GetActorLocation()-Encounter->Convoy[0]->GetActorLocation()).GetSafeNormal2D()*225;
            const bool HasGoal=Benchmark ? (Ground=Goal,true) : Escort
                ? WarSiegeNavigation::ConvoyApproach(Pawn,Goal,Offset,Encounter->Battlefield->ObjectiveRadius,Encounter,Ground,Formation)
                : WarSiegeNavigation::Approach(Pawn,Goal,Offset,Encounter->Battlefield->ObjectiveRadius,Ground);
            if (HasGoal)
            {
                const auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(),Pawn->GetActorLocation(),Ground,Pawn,WarSiegeNavigation::FilterFor(Pawn));
                if (Path && Path->IsValid() && !Path->IsPartial() && Path->PathPoints.Num()>1
                    && (!Escort || WarSiegeNavigation::ConvoyPathClear(Pawn,Encounter,Path->PathPoints)))
                { int32 Point=1; while (Point<Path->PathPoints.Num()-1 && FVector::Dist2D(Pawn->GetActorLocation(),Path->PathPoints[Point])<(Benchmark ? 10 : Escort ? 20 : 100)) ++Point;
                  Waypoints.Add(Pawn,Path->PathPoints[Point]); }
                else Waypoints.Remove(Pawn);
            }
            else Waypoints.Remove(Pawn);
            if (ClearVehicle) continue;
            const bool Healed=!Benchmark && HealNearby(Pawn,Runtime,Catalog,Encounter); if (Healed) ++Actions;
            // A genuine catalog self-buff exercises ordinary resource/cooldown rules even when the approach has no enemy in range.
            if (bLiveDefended && Actions==0 && Catalog && !Healed)
                for (const auto* Ability:Catalog->Kit(Pawn->GetCareerId()))
                {
                    if (Ability->bEnemyTarget || (Ability->TargetKind!=TEXT("self") && Ability->TargetKind!=TEXT("ally"))
                        || !Ability->Effects.ContainsByPredicate([](const auto& Effect) {
                            return Effect.Kind==TEXT("player_status") && Effect.Duration>0;
                        }) || Ability->Effects.ContainsByPredicate([](const auto& Effect) {
                            return Effect.Kind!=TEXT("player_status") || (!Effect.Recipient.IsNone() && Effect.Recipient!=TEXT("caster")); })) continue;
                    FString AbilityError;
                    if (Runtime->TryActivate(Ability->Id,Pawn,AbilityError)) { ++Actions;break; }
                }
            if (Enemy && Catalog && !Healed)
            {
                PC->SetControlRotation((Enemy->GetActorLocation()-Pawn->GetActorLocation()).Rotation());
                for (const auto* Ability:Catalog->Kit(Pawn->GetCareerId()))
                {
                    if (!Ability->Effects.ContainsByPredicate([](const auto& E) { return E.Kind==TEXT("damage") || E.Kind==TEXT("status"); })) continue;
                    FString Error;
                    AActor* Aim=Ability->bEnemyTarget ? static_cast<AActor*>(Enemy) : Pawn;
                    if (Ability->RequiresStationary())
                    {
                        if (!Runtime->CanPrepareStationaryCast(*Ability,Aim,Error)) continue;
                        Pawn->GetCharacterMovement()->StopMovementImmediately(); Runtime->UpdateMovementIntent(false);
                    }
                    if (Runtime->TryActivate(Ability->Id,Aim,Error)) { ++Actions; break; }
                }
                if (!Runtime->IsBusy()) Pawn->RequestTargetStrike(Enemy);
            }
        }
        FVector FormationGoal;const bool Formation=BenchmarkGoal(I,FormationGoal);
        const bool Escort=Attacker && !bLiveDefended && !Formation && Encounter->Siege.Stage==0 && Encounter->Siege.Objective>0 && Encounter->Convoy.Num()==2;
        if (!Runtime->IsStationaryCast() && !Runtime->OwnsMovement()) if (const auto* Waypoint=Waypoints.Find(Pawn);
            Waypoint && FVector::Dist2D(Pawn->GetActorLocation(),*Waypoint)>(Formation ? 10 : Escort ? 5 : 70))
        {
            const float Half=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
            const TArray<FVector> Segment={Pawn->GetActorLocation()-FVector(0,0,Half+3),*Waypoint};
            if (!Escort || WarSiegeNavigation::ConvoyPathClear(Pawn,Encounter,Segment))
                Pawn->AddMovementInput((*Waypoint-Pawn->GetActorLocation()).GetSafeNormal2D());
            else { Waypoints.Remove(Pawn);Pawn->GetCharacterMovement()->StopMovementImmediately(); }
        }
    }
    MaxAegis=FMath::Max(MaxAegis,Counts[0]); MaxRiftbound=FMath::Max(MaxRiftbound,Counts[1]);
    bConcurrentSides|=Encounter->Siege.Stage==1 && Encounter->Siege.LeftProgress>0 && Encounter->Siege.RightProgress>0;
    bLockedCenter|=Encounter->Siege.Stage==1 && !WarSiege::CenterUnlocked(Encounter->Siege) && Encounter->Siege.Progress==0;
}
bool UWarCitadelSiegeProof::ExpectedFinishedOutcome(const FWarSiegeState& State) const
{
    if (State.Phase!=EWarSiegePhase::Finished) return false;
    if (bLive && bLiveDefended)
        return !State.bAttackersWon && State.RulesVersion==2 && State.Stage==0 && State.Objective==0 && State.MainClaims==0
            && !State.bOvertime && State.Elapsed+1.e-6>=WarSiege::StageSeconds && State.Elapsed<=WarSiege::StageSeconds+.05+1.e-6;
    return Round==1 ? State.bAttackersWon && State.MainClaims==0xff
        : !State.bAttackersWon && State.Elapsed+1.e-6>=WarSiege::StageSeconds;
}
bool UWarCitadelSiegeProof::LiveCharacterWitnesses(TArray<TSharedPtr<FJsonValue>>& Rows,FString& Error) const
{
    if (!bLive || LiveIds.Num()!=36 || LivePlayers.Num()!=36 || LiveInitialInventories.Num()!=36)
    { Error=TEXT("The live fixture lacks its complete ordinary character baseline.");return false; }
    for (int32 I=0;I<LivePlayers.Num();++I)
    {
        const auto* Player=LivePlayers[I].Get();const auto* PS=Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        const auto* Pawn=Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
        FString Inventory;const auto* Before=Player ? LiveInitialInventories.Find(Player->ScenarioCharacterId) : nullptr;
        if (!PS || !Before || Player->ScenarioCharacterId!=LiveIds[I] || PS->GetRealm()!=(I<18 ? EWarRealm::Aegis : EWarRealm::Riftbound)
            || PS->IsSiegeNormalized() || PS->GetCombatLevel()!=40
            || !FJsonObjectConverter::UStructToJsonObjectString(PS->GetInventory(),Inventory) || Inventory!=*Before
            || (PS->IsScenarioTransferPending() && Pawn && Pawn->GetCharacterMovement()->MovementMode!=MOVE_None))
        { Error=TEXT("The defended live result lost its normal inventory, progression, equipment or custody movement hold.");return false; }
        FString InitialHash,CurrentHash;
        if (!WarCitadelProofHash::Text(*Before,InitialHash,Error) || !WarCitadelProofHash::Text(Inventory,CurrentHash,Error)) return false;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("characterId"),Player->ScenarioCharacterId);
        Row->SetStringField(TEXT("realm"),PS->GetRealm()==EWarRealm::Aegis ? TEXT("aegis") : TEXT("riftbound"));
        Row->SetBoolField(TEXT("normalized"),PS->IsSiegeNormalized());Row->SetNumberField(TEXT("combatLevel"),PS->GetCombatLevel());
        Row->SetBoolField(TEXT("inventoryUnchanged"),Inventory==*Before);Row->SetStringField(TEXT("initialInventorySha256"),InitialHash);
        Row->SetStringField(TEXT("inventorySha256"),CurrentHash);Row->SetNumberField(TEXT("inventoryRevision"),PS->GetInventory().Revision);
        Row->SetBoolField(TEXT("transferPending"),PS->IsScenarioTransferPending());Row->SetBoolField(TEXT("movementHeld"),Pawn && Pawn->GetCharacterMovement()->MovementMode==MOVE_None);
        Row->SetBoolField(TEXT("hasAvatar"),Pawn!=nullptr);Row->SetBoolField(TEXT("alive"),Pawn && !Pawn->IsDead());
        Row->SetBoolField(TEXT("modelReady"),Pawn && Pawn->IsVisualReady());Row->SetStringField(TEXT("zone"),PS->GetCurrentZone().ToString());
        Row->SetNumberField(TEXT("health"),PS->GetAttributes()->GetHealth());Row->SetNumberField(TEXT("mana"),PS->GetAttributes()->GetMana());
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    return true;
}
void UWarCitadelSiegeProof::ObserveLockedCenter()
{
    if (bLockedCenterPhysical || bPerformance || !Encounter) return;
    const auto& State=Encounter->Siege;
    const double SampleAt=Encounter->LastPresenceSampleAt,Age=GetWorld()->GetTimeSeconds()-SampleAt;
    const int32 Attackers=Encounter->LastSampledPresence.Attackers;
    if (State.Phase!=EWarSiegePhase::Active || State.Stage!=1 || State.RulesVersion!=2
        || WarSiege::CenterUnlocked(State) || State.Progress!=0 || Attackers<2 || SampleAt<0 || Age<0 || Age>.25)
    { LockedCenterSince=LockedCenterLastSample=-1;LockedCenterObservations.Reset();return; }
    if (SampleAt<=LockedCenterLastSample || (LockedCenterLastSample>=0 && SampleAt-LockedCenterLastSample<.25)) return;
    if (LockedCenterLastSample<0 || SampleAt-LockedCenterLastSample>.5)
    { LockedCenterSince=SampleAt;LockedCenterObservations.Reset(); }
    LockedCenterLastSample=SampleAt;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("presenceSampleAt"),SampleAt);
    Row->SetNumberField(TEXT("qualifyingAttackers"),Attackers);Row->SetNumberField(TEXT("progress"),State.Progress);
    Row->SetBoolField(TEXT("locked"),true);LockedCenterObservations.Add(MakeShared<FJsonValueObject>(Row));
    LockedCenterPhysicalSeconds=SampleAt-LockedCenterSince;
    bLockedCenterPhysical=LockedCenterPhysicalSeconds>=1 && LockedCenterObservations.Num()>=4;
}
void UWarCitadelSiegeProof::Drive()
{
    if (!Encounter || !Encounter->Battlefield || Encounter->Siege.Phase != EWarSiegePhase::Active) return;
    const auto& S = Encounter->Siege;
    int32 Counts[2] = {};
    for (auto Seat=TacticalSeats.CreateIterator();Seat;++Seat) if (!Seat.Key().IsValid()) Seat.RemoveCurrent();
    const auto* Catalog = GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    for (TActorIterator<AWarSiegeBotController> It(GetWorld()); It; ++It)
    {
        auto* Bot = *It; auto* PS = Bot->GetPlayerState<AWarPlayerState>();
        auto* Pawn = Cast<AWarCharacter>(Bot->GetPawn());
        if (!PS || !Encounter->Owns(PS) || Bot->Unit != EWarSiegeUnit::Participant) continue;
        const bool Attacker = PS->GetRealm() == EWarRealm::Riftbound;
        const int32 Team = Attacker ? 1 : 0;int32 Slot=0;
        // Surviving controllers retain their seats; replacements reclaim vacancies.
        {
            if (const int32* Existing=TacticalSeats.Find(Bot)) Slot=*Existing%18;
            else
            {
                Slot=0;
                while (Slot<18)
                {
                    bool Used=false;
                    for (const auto& Seat:TacticalSeats) Used|=Seat.Value==Team*18+Slot;
                    if (!Used) break;++Slot;
                }
                if (Slot>=18) { Finish(false,TEXT("The fixture encountered more than 18 seats in one realm."));return; }
                TacticalSeats.Add(Bot,Team*18+Slot);
            }
        }
        if (!Pawn || Pawn->IsDead() || !Pawn->IsVisualReady()) continue;
        ++Counts[Team]; Bot->SetActorTickEnabled(false);
        const FVector Current = Pawn->GetActorLocation();
        if (const auto* Previous = Positions.Find(Pawn)) Movement += FVector::Dist2D(Current, *Previous);
        Positions.Add(Pawn, Current);
        // Script tactics through ordinary path following and combat. Captures, timers,
        // gates, equipment movement, deaths and outcomes are never assigned by this fixture.
        const bool DefendedRound = Round == 2;
        FVector Goal = Encounter->Battlefield->TeamSpawns[S.Stage * 2 + Team];
        if (Attacker && (!DefendedRound || S.Elapsed < 20)) Goal = Encounter->TaskLocation(Slot & 1);
        if (!Attacker && DefendedRound && S.Elapsed < 20) Goal = Encounter->TaskLocation();
        const bool CenterProbe=Attacker && Slot<2 && !DefendedRound && !bPerformance && !bLockedCenterPhysical
            && S.Stage==1 && !WarSiege::CenterUnlocked(S);
        if (CenterProbe) Goal=Encounter->Battlefield->Objective(1,2);
        const bool Benchmark=BenchmarkGoal(Team*18+Slot,Goal);
        const bool Escort=Attacker && !DefendedRound && !Benchmark && S.Stage==0 && S.Objective>0 && Encounter->Convoy.Num()==2;
        const bool ClearVehicle=Escort && !WarSiegeNavigation::ConvoyPositionClear(Pawn,Encounter);
        const bool KeepEscort=Escort && (Slot%3==0 || ClearVehicle);
        auto* Runtime=PS->GetClassAbilities();
        if (ClearVehicle && Runtime->IsStationaryCast()) Runtime->UpdateMovementIntent(true);
        if (Runtime->IsStationaryCast() || Runtime->OwnsMovement()) { Bot->StopMovement();continue; }
        AWarCharacter* Enemy = nullptr;
        double Nearest = FMath::Square(2500.);
        if (Attacker && !DefendedRound && !Benchmark)
            for (TActorIterator<AWarCharacter> Other(GetWorld()); Other; ++Other)
            {
                const double Distance = FVector::DistSquared(Current, Other->GetActorLocation());
                if (Distance < Nearest && WarCitadelProofTactics::CanTarget(Encounter,Pawn,*Other,2500))
                { Nearest = Distance; Enemy = *Other; }
            }
        if (Enemy && !KeepEscort && !CenterProbe) Goal = Enemy->GetActorLocation();
        FVector Ground;
        const float Angle = Slot * 2.399963f;
        const bool Formation=Escort && (KeepEscort || !Enemy);
        FVector Offset(FMath::Cos(Angle)*360,FMath::Sin(Angle)*360,0);
        if (Formation) Offset=WarSiegeEscort::Offset(Slot,Encounter->Convoy[0]->GetActorRotation().Yaw);
        else if (Escort && Enemy) Offset=(Enemy->GetActorLocation()-Encounter->Convoy[0]->GetActorLocation()).GetSafeNormal2D()*225;
        const bool HasGoal=Benchmark ? (Ground=Goal,true) : Escort
            ? WarSiegeNavigation::ConvoyApproach(Pawn,Goal,Offset,Encounter->Battlefield->ObjectiveRadius,Encounter,Ground,Formation)
            : WarSiegeNavigation::Approach(Pawn,Goal,Offset,Encounter->Battlefield->ObjectiveRadius,Ground);
        if (HasGoal)
        {
            if (Bot->GetMoveStatus() != EPathFollowingStatus::Moving
                || FVector::DistSquared(Bot->LastMoveGoal,Ground) > FMath::Square(Escort ? 35.f : 150.f))
            { Bot->MoveToLocation(Ground, Benchmark ? 10 : Escort ? 25 : 60, false); Bot->LastMoveGoal = Ground; }
        }
        else if (Escort) Bot->StopMovement();
        if (ClearVehicle || !Catalog) continue;
        if (!Benchmark && HealNearby(Pawn,Runtime,Catalog,Encounter)) { ++Actions; if (Runtime->IsStationaryCast()) Bot->StopMovement(); continue; }
        if (!Enemy) { Bot->ClearFocus(EAIFocusPriority::Gameplay);continue; }
        Bot->SetFocus(Enemy);
        for (const auto* Ability : Catalog->Kit(Pawn->GetCareerId()))
        {
            if (!Ability->Effects.ContainsByPredicate([](const auto& Effect) { return Effect.Kind == TEXT("damage") || Effect.Kind == TEXT("status"); })) continue;
            FString Error;
            AActor* Aim=Ability->bEnemyTarget ? static_cast<AActor*>(Enemy) : Pawn;
            if (Ability->RequiresStationary())
            {
                if (!Runtime->CanPrepareStationaryCast(*Ability,Aim,Error)) continue;
                Bot->StopMovement(); Pawn->GetCharacterMovement()->StopMovementImmediately(); Runtime->UpdateMovementIntent(false);
            }
            if (Runtime->TryActivate(Ability->Id,Aim,Error))
            { ++Actions; break; }
        }
        if (Runtime->IsStationaryCast() || Runtime->OwnsMovement()) Bot->StopMovement();
        else { Pawn->RequestTargetStrike(Enemy); if (!Escort) Bot->MoveToActor(Enemy,100,false); }
    }
    MaxAegis = FMath::Max(MaxAegis, Counts[0]); MaxRiftbound = FMath::Max(MaxRiftbound, Counts[1]);
    bConcurrentSides |= S.Stage == 1 && S.LeftProgress > 0 && S.RightProgress > 0;
    bLockedCenter |= S.Stage == 1 && !WarSiege::CenterUnlocked(S) && S.Progress == 0;
    bSawContest |= Encounter->bContested;
}
TSharedPtr<FJsonObject> UWarCitadelSiegeProof::PhysicalSnapshot() const
{
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("version"),1);
    Result->SetBoolField(TEXT("diagnosticOnly"),true);
    if (!Encounter || !Encounter->Battlefield) { Result->SetBoolField(TEXT("available"),false);return Result; }
    Result->SetBoolField(TEXT("available"),true);
    Result->SetNumberField(TEXT("presenceSampleAt"),Encounter->LastPresenceSampleAt);
    Result->SetNumberField(TEXT("presenceAgeSeconds"),Encounter->LastPresenceSampleAt<0 ? -1 : GetWorld()->GetTimeSeconds()-Encounter->LastPresenceSampleAt);
    const auto& Presence=Encounter->LastSampledPresence;
    Result->SetNumberField(TEXT("qualifyingAttackers"),Presence.Attackers);
    Result->SetNumberField(TEXT("qualifyingDefenders"),Presence.Defenders);
    Result->SetBoolField(TEXT("crewReady"),Presence.bCrewAlive);
    Result->SetBoolField(TEXT("escortAtCheckpoint"),Presence.bEscortAtCheckpoint);
    Result->SetNumberField(TEXT("crewReplacementAt"),Encounter->CrewAt);
    TArray<TSharedPtr<FJsonValue>> Participants;
    for (TActorIterator<AWarSiegeBotController> It(GetWorld());It;++It)
    {
        const auto* Bot=*It;const auto* State=Bot->GetPlayerState<AWarPlayerState>();
        const auto* Pawn=Cast<AWarCharacter>(Bot->GetPawn());
        if (!State || !Encounter->Owns(State) || Bot->Unit!=EWarSiegeUnit::Participant || !Pawn) continue;
        if (Participants.Num()>=36) break;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("actor"),Pawn->GetPathName());
        Row->SetBoolField(TEXT("attacker"),State->GetRealm()==EWarRealm::Riftbound);
        Row->SetArrayField(TEXT("position"),JsonPoint(Pawn->GetActorLocation()));
        Row->SetArrayField(TEXT("lastMoveGoal"),JsonPoint(Bot->LastMoveGoal));
        Row->SetNumberField(TEXT("moveStatus"),int32(Bot->GetMoveStatus()));
        Row->SetBoolField(TEXT("dead"),Pawn->IsDead());Row->SetBoolField(TEXT("visualReady"),Pawn->IsVisualReady());
        Row->SetBoolField(TEXT("protected"),Encounter->IsProtected(Pawn));
        Row->SetBoolField(TEXT("stationaryCast"),State->GetClassAbilities()->IsStationaryCast());
        Row->SetBoolField(TEXT("abilityOwnsMovement"),State->GetClassAbilities()->OwnsMovement());
        Row->SetNumberField(TEXT("health"),State->GetAttributes()->GetHealth());Participants.Add(MakeShared<FJsonValueObject>(Row));
    }
    Result->SetArrayField(TEXT("participants"),Participants);
    Result->SetNumberField(TEXT("convoyCount"),Encounter->Convoy.Num());
    TArray<TSharedPtr<FJsonValue>> Vehicles;
    for (const auto& Vehicle:Encounter->Convoy)
    {
        if (Vehicles.Num()>=2) break;
        if (!IsValid(Vehicle) || Vehicle->GetOwner()!=Encounter) continue;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("actor"),Vehicle->GetPathName());
        Row->SetArrayField(TEXT("position"),JsonPoint(Vehicle->GetActorLocation()));
        Row->SetNumberField(TEXT("yaw"),Vehicle->GetActorRotation().Yaw);Row->SetNumberField(TEXT("travelCm"),Vehicle->Travel);
        Row->SetBoolField(TEXT("moving"),Vehicle->bMoving);Row->SetBoolField(TEXT("placed"),Vehicle->IsPlaced());
        Row->SetBoolField(TEXT("crewReady"),Vehicle->HasCrew());
        Row->SetArrayField(TEXT("routeGoal"),JsonPoint(Vehicle->RouteGoal));
        Row->SetNumberField(TEXT("remainingPathPoints"),Vehicle->Route.Num());
        if (!Vehicle->Route.IsEmpty()) Row->SetArrayField(TEXT("nextPathPoint"),JsonPoint(Vehicle->Route[0]));
        Row->SetNumberField(TEXT("checkpointDistanceCm"),FVector::Dist2D(Vehicle->GetActorLocation(),Encounter->Battlefield->EquipmentDestination(Encounter->Siege.Objective)));
        Row->SetNumberField(TEXT("recoveryDisplacements"),Vehicle->RecoveryDisplacements);
        Row->SetNumberField(TEXT("projectedStartSkips"),Vehicle->ProjectedStartSkips);
        if (Vehicle->Definition) Row->SetArrayField(TEXT("hullExtentCm"),JsonPoint(Vehicle->Definition->HullExtent));
        TArray<TSharedPtr<FJsonValue>> Crew;
        for (const auto& Engineer:Vehicle->Engineers)
        {
            if (Crew.Num()>=2) break;
            auto Person=MakeShared<FJsonObject>();Person->SetBoolField(TEXT("present"),IsValid(Engineer));
            if (IsValid(Engineer))
            {
                Person->SetStringField(TEXT("actor"),Engineer->GetPathName());Person->SetBoolField(TEXT("dead"),Engineer->IsDead());
                Person->SetBoolField(TEXT("visualReady"),Engineer->IsVisualReady());
                const auto* State=Engineer->GetPlayerState<AWarPlayerState>();
                Person->SetBoolField(TEXT("encounterOwned"),State && Encounter->Owns(State));
                if (State) { Person->SetNumberField(TEXT("health"),State->GetAttributes()->GetHealth());Person->SetNumberField(TEXT("maxHealth"),State->GetAttributes()->GetMaxHealth()); }
            }
            Crew.Add(MakeShared<FJsonValueObject>(Person));
        }
        Row->SetArrayField(TEXT("engineers"),Crew);Vehicles.Add(MakeShared<FJsonValueObject>(Row));
    }
    Result->SetArrayField(TEXT("vehicles"),Vehicles);return Result;
}
void UWarCitadelSiegeProof::Finish(bool Passed, const FString& Detail)
{
    if (bRecoveryProof) { FinishRecovery(Passed,Detail);return; }
    bFinished = true;
    FString PerformanceError;Passed&=FinishPerformance(Passed,PerformanceError);
    auto Report = MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("passed"), Passed); Report->SetStringField(TEXT("detail"), Detail);
    Report->SetBoolField(TEXT("diagnosticOnly"),DiagnosticSeconds>0);
    Report->SetBoolField(TEXT("diagnosticSampleComplete"),bDiagnosticComplete);
    Report->SetNumberField(TEXT("diagnosticSeconds"),DiagnosticSeconds);
    Report->SetNumberField(TEXT("diagnosticElapsedSeconds"),DiagnosticStartedAt<0 ? 0 : GetWorld()->GetTimeSeconds()-DiagnosticStartedAt);
    Report->SetStringField(TEXT("map"), Map); Report->SetStringField(TEXT("signature"), Signature);
    Report->SetStringField(TEXT("cityRevision"), Revision); Report->SetStringField(TEXT("mapSha256"), MapHash);
    Report->SetBoolField(TEXT("proofOnly"), true); Report->SetBoolField(TEXT("transientReviewOverride"), bFixtureReview);
    Report->SetBoolField(TEXT("humanPlaytest"), false); Report->SetBoolField(TEXT("productionAdmission"), false);
    Report->SetBoolField(TEXT("steamAdmission"), false); Report->SetBoolField(TEXT("visualApproval"), false);
    Report->SetBoolField(TEXT("reconnectVerified"), false); Report->SetBoolField(TEXT("normalCharacterRecoveryVerified"), false);
    Report->SetBoolField(TEXT("campaignHumanEnrollmentVerified"), false);
    Report->SetBoolField(TEXT("syntheticNormalControllers"), bLive);
    const auto* Bridge=bLive ? GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>() : nullptr;
    const bool Acknowledged=Bridge && Bridge->SettlementAcknowledged(PendingSettlement,!bLiveDefended);
    Report->SetBoolField(TEXT("trustedSettlementAcknowledged"),Acknowledged);
    Report->SetBoolField(TEXT("serviceOperationsVerified"),false);
    Report->SetBoolField(TEXT("nonparticipantEvacuationVerified"),false);
    if (bLive)
    {
        const FString Outcome=bLiveDefended ? TEXT("city_defended") : TEXT("city_captured");
        Report->SetStringField(TEXT("campaignOutcome"),Outcome);
        Report->SetStringField(TEXT("trustedSettlementResult"),Acknowledged ? Outcome : FString());
        Report->SetStringField(TEXT("settledActivationId"),PendingSettlement);
        Report->SetBoolField(TEXT("preparationObserved"),bLivePreparationObserved);
        Report->SetBoolField(TEXT("servicesSuspendedObserved"),bLiveServicesSuspendedObserved);
        Report->SetBoolField(TEXT("servicesRestoredObserved"),Acknowledged && !AWarSiegeEncounter::Capital(GetWorld()));
        Report->SetBoolField(TEXT("custodyMovementHeldObserved"),bLiveCustodyHeldObserved);
        if (bLiveDefended)
        {
            TArray<TSharedPtr<FJsonValue>> Characters;FString CharacterError;
            Passed&=LiveCharacterWitnesses(Characters,CharacterError);Report->SetArrayField(TEXT("normalCharacters"),Characters);
            if (!CharacterError.IsEmpty()) Report->SetStringField(TEXT("detail"),CharacterError);
            Report->SetBoolField(TEXT("passed"),Passed);
        }
    }
    Report->SetBoolField(TEXT("concurrentSides"), bConcurrentSides); Report->SetBoolField(TEXT("lockedCenterObserved"), bLockedCenter);
    Report->SetBoolField(TEXT("lockedCenterPhysicallyOccupied"),bLockedCenterPhysical);
    Report->SetNumberField(TEXT("lockedCenterPhysicalSeconds"),LockedCenterPhysicalSeconds);
    Report->SetArrayField(TEXT("lockedCenterPhysicalSamples"),LockedCenterObservations);
    Report->SetBoolField(TEXT("physicalContestObserved"), bSawContest);
    Report->SetBoolField(TEXT("encounterScopedCleanupVerified"), !bLive && bSentinelIntact);
    Report->SetNumberField(TEXT("maxAegis"), MaxAegis); Report->SetNumberField(TEXT("maxRiftbound"), MaxRiftbound);
    Report->SetNumberField(TEXT("movementCm"), Movement); Report->SetNumberField(TEXT("normalAbilityActivations"), Actions);
    Report->SetArrayField(TEXT("rounds"), Rounds); Report->SetArrayField(TEXT("samples"), Samples);
    Report->SetBoolField(TEXT("renderedPerformanceRequested"),bPerformance);
    Report->SetBoolField(TEXT("performanceBaseline"),bPerformanceBaseline);Report->SetBoolField(TEXT("isolatedStageWindows"),false);
    if (bPerformanceBaseline)
    {
        Report->SetStringField(TEXT("fixtureMode"),BaselineFixtureMode);
        Report->SetBoolField(TEXT("earnedProgressionObserved"),bBaselineSettled);
        Report->SetObjectField(TEXT("baselineProgression"),BaselineProgression());
        for (const TCHAR* Flag:{TEXT("progressionAcceptance"),TEXT("victoryAcceptance"),TEXT("conquestAcceptance"),TEXT("routeAcceptance"),TEXT("fullSiegeAdmission")})
            Report->SetBoolField(Flag,false);
    }
    if (!PerformanceError.IsEmpty()) Report->SetStringField(TEXT("performanceDetail"),PerformanceError);
    FString Text; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
    FFileHelper::SaveStringToFile(Text, *(FPaths::GetPath(ConfigPath) / TEXT("report.json")));
    UE_LOG(LogTemp, Display, TEXT("WAR_CITADEL_SIEGE_PROOF passed=%d detail=%s"), Passed, *Detail);
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}
void UWarCitadelSiegeProof::Tick(float Delta)
{
    if (bFinished || !GetWorld()->HasBegunPlay() || GetWorld()->GetNetMode() == NM_Client) return;
    FString Error;
    if (!bLoaded && !Load(Error)) { Finish(false, Error); return; }
    if (bRecoveryProof) { TickRecovery();return; }
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now - Began > MaxElapsed) { Finish(false, TEXT("The real-time physical siege fixture or trusted settlement did not complete.")); return; }
    if (bLive && !PendingSettlement.IsEmpty())
    {
        const auto* Bridge=GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>();
        if (Bridge && Bridge->SettlementAcknowledged(PendingSettlement,!bLiveDefended))
            Finish(MaxAegis==18 && MaxRiftbound==18 && Actions>0 && (!bLiveDefended ? bConcurrentSides && bLockedCenter && (bPerformance || bLockedCenterPhysical)
                : Movement>10000 && bLivePreparationObserved && bLiveServicesSuspendedObserved && bLiveCustodyHeldObserved),
                bLiveDefended ? TEXT("Synthetic normal 18v18 stage defense timed out through ordinary rules and the real private Node authority acknowledged city defense.")
                    : TEXT("Synthetic normal 18v18 combat completed and the real private Node authority acknowledged settlement."));
        return;
    }
    if (Sentinel)
    {
        const auto* PS = Sentinel->GetPlayerState<AWarPlayerState>();
        bSentinelIntact &= IsValid(Sentinel) && PS && !PS->IsSiegeMember() && !PS->IsSiegeNormalized()
            && FMath::IsNearlyEqual(PS->GetAttributes()->GetHealth(),73.f)
            && FMath::IsNearlyEqual(PS->GetAttributes()->GetMana(),61.f);
        if (!bSentinelIntact) { Finish(false,TEXT("Encounter transitions altered an unrelated normal avatar.")); return; }
    }
    if (Now - Began > MaxElapsed) { Finish(false, TEXT("The real-time physical siege fixture did not complete both outcomes.")); return; }
    if (!Round)
    { if (Now - Began < 20) return; if (!Start(Error) && Now - Began > 180 && !Error.IsEmpty()) Finish(false, Error); return; }
    if (!Encounter) { Finish(false, TEXT("The encounter disappeared before its durable outcome.")); return; }
    ObserveLockedCenter();
    if (!ObserveBaselineProgression(Error)) { Finish(false,Error);return; }
    if (bLive) DriveLivePlayers();
    else if (Now >= NextDrive) { NextDrive = Now + .25; Drive(); }
    SamplePerformance();
    if (bFinished) return;
    if (bPerformanceBaseline)
    {
        const auto Window=PerformanceWindows[2]->AsObject();
        if (Encounter->Siege.Stage==2 && Encounter->Siege.Phase==EWarSiegePhase::Active && Encounter->Siege.MainClaims==0x7f
            && Window->GetNumberField(TEXT("endElapsedSeconds"))-Window->GetNumberField(TEXT("startElapsedSeconds"))>=60)
        {
            if (!ObserveBaselineProgression(Error,true)) { Finish(false,Error);return; }
            bBaselineSettled=true;
            Finish(true,TEXT("The unchanged city earned seven real capture milestones and three crowd windows; commander victory was not claimed."));return;
        }
        return;
    }
    if (Now >= NextSample)
    {
        NextSample = Now + 10;
        auto Row = UWarCampaignSiegeSubsystem::Snapshot(Encounter->Siege, Encounter->bPreparing,
            FMath::Max(0.,Encounter->PreparationUntil - Now));
        Row->SetNumberField(TEXT("round"), Round); Row->SetNumberField(TEXT("deaths"), Encounter->Deaths);
        if (!bPerformance) Row->SetObjectField(TEXT("physical"),PhysicalSnapshot());
        if (DiagnosticSeconds>0) Row->SetNumberField(TEXT("diagnosticElapsedSeconds"),Now-DiagnosticStartedAt);
        Samples.Add(MakeShared<FJsonValueObject>(Row));
    }
    if (DiagnosticSeconds>0 && DiagnosticStartedAt>=0 && Now-DiagnosticStartedAt>=DiagnosticSeconds
        && Encounter->Siege.Phase!=EWarSiegePhase::Finished)
    { bDiagnosticComplete=true;Finish(false,TEXT("Bounded physical diagnostic completed; encounter outcome remains unverified."));return; }
    if (Encounter->Siege.Phase != EWarSiegePhase::Finished) return;
    auto Result = UWarCampaignSiegeSubsystem::Snapshot(Encounter->Siege, false);
    Result->SetNumberField(TEXT("round"), Round); Rounds.Add(MakeShared<FJsonValueObject>(Result));
    const bool Correct = ExpectedFinishedOutcome(Encounter->Siege);
    if (!Correct) { Finish(false, TEXT("A scripted tactic produced the wrong authoritative outcome.")); return; }
    if (bLive)
    { PendingSettlement=Encounter->ActivationId; return; }
    if (Round == 1)
    { Encounter->ResetRound(); Positions.Reset(); if (!Start(Error)) Finish(false, Error); return; }
    Finish(MaxAegis == 18 && MaxRiftbound == 18 && bConcurrentSides && bLockedCenter && (bPerformance || bLockedCenterPhysical) && Movement > 10000 && Actions > 0,
        TEXT("Physical 18v18 full siege and defended timeout completed using normal encounter rules."));
}
