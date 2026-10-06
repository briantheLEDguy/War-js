#include "WarScenarioInstance.h"
#include "WarScenarioTransport.h"
#include "WarPlayerController.h"
#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarPlayerState.h"
#include "WarSiegeBattlefield.h"
#include "WarCityDefinition.h"
#include "WarCitadelSiegeProof.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "HAL/FileManager.h"
#include "Modules/ModuleManager.h"
#include "EngineUtils.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameSession.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
    bool ProofString(const TSharedPtr<FJsonObject>& Row,const TCHAR* Key,const FString& Expected)
    { FString Value;return Row && Row->HasTypedField<EJson::String>(Key) && Row->TryGetStringField(Key,Value) && Value.Equals(Expected,ESearchCase::CaseSensitive); }
    bool ProofNumber(const TSharedPtr<FJsonObject>& Row,const TCHAR* Key,double Expected)
    { double Value=0;return Row && Row->HasTypedField<EJson::Number>(Key) && Row->TryGetNumberField(Key,Value) && Value==Expected; }
    bool ProofBool(const TSharedPtr<FJsonObject>& Row,const TCHAR* Key,bool Expected)
    { bool Value=false;return Row && Row->HasTypedField<EJson::Boolean>(Key) && Row->TryGetBoolField(Key,Value) && Value==Expected; }
    bool ProofHash(const FString& Value)
    { if (Value.Len()!=64) return false;for (TCHAR C:Value) if (!((C>='0' && C<='9') || (C>='a' && C<='f'))) return false;return true; }
    bool ProofGuid(const FString& Value,bool Version4=false)
    {
        FGuid Id;
        return FGuid::ParseExact(Value,EGuidFormats::DigitsWithHyphens,Id) && Id.IsValid()
            && Id.ToString(EGuidFormats::DigitsWithHyphens).ToLower()==Value
            && (!Version4 || (Value[14]=='4' && (Value[19]=='8' || Value[19]=='9' || Value[19]=='a' || Value[19]=='b')));
    }
    FString ScenarioProofRoot(const TSharedPtr<FJsonObject>& Proof)
    { return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("../../artifacts/unreal/scenario-menu")/Proof->GetStringField(TEXT("fixtureId"))/TEXT("host")); }
    bool SameFileHash(const FString& Filename,const FString& Expected,FString& Error)
    { FString Actual;return ProofHash(Expected) && WarCitadelProofHash::File(Filename,Actual,Error) && Actual==Expected; }
    bool SameHashMap(const TSharedPtr<FJsonObject>& Expected,const TSharedPtr<FJsonObject>& Actual)
    {
        if (!Expected || !Actual || Expected->Values.Num()!=Actual->Values.Num()) return false;
        for (const auto& Pair:Expected->Values)
        { FString Hash;if (!Pair.Value->TryGetString(Hash) || !ProofString(Actual,*FString(*Pair.Key),Hash)) return false; }
        return true;
    }
}

bool WarScenarioCandidateProof::LoopbackUrl(const FString& Url)
{
    const FString Prefix=TEXT("http://127.0.0.1:");const FString Port=Url.Mid(Prefix.Len());
    if (!Url.StartsWith(Prefix) || Port.IsEmpty() || Port.Len()>5) return false;
    for (TCHAR C:Port) if (C<'0' || C>'9') return false;
    return FCString::Atoi(*Port)>0 && FCString::Atoi(*Port)<=65535;
}

bool WarScenarioCandidateProof::Identity(const TSharedPtr<FJsonObject>& Proof,FString& Error)
{
    Error.Reset();FString Fixture,Map,Signature,Geometry,Revision,MapHash;
    const TSharedPtr<FJsonObject>* Definition=nullptr;
    if (!Proof || !ProofNumber(Proof,TEXT("schemaVersion"),1) || !ProofBool(Proof,TEXT("proofOnly"),true)
        || !ProofBool(Proof,TEXT("contentReviewOverride"),true) || !ProofBool(Proof,TEXT("productionAdmission"),false)
        || !ProofBool(Proof,TEXT("steamAdmission"),false) || !ProofBool(Proof,TEXT("territorialAcceptance"),false)
        || !ProofBool(Proof,TEXT("releaseApproved"),false) || !ProofString(Proof,TEXT("scenario"),TEXT("lower_city"))
        || !ProofNumber(Proof,TEXT("capacity"),18) || !ProofNumber(Proof,TEXT("rulesVersion"),2)
        || !ProofString(Proof,TEXT("battlefield"),TEXT("FullSiege")) || !ProofString(Proof,TEXT("statsMode"),TEXT("scenario"))
        || !Proof->TryGetStringField(TEXT("fixtureId"),Fixture) || !ProofGuid(Fixture,true)
        || !Proof->TryGetStringField(TEXT("map"),Map) || !Proof->TryGetStringField(TEXT("signature"),Signature) || !ProofHash(Signature)
        || !Proof->TryGetStringField(TEXT("geometrySignature"),Geometry) || !ProofHash(Geometry)
        || !Proof->TryGetStringField(TEXT("cityRevision"),Revision) || !ProofHash(Revision)
        || !Proof->TryGetStringField(TEXT("mapSha256"),MapHash) || !ProofHash(MapHash)
        || !Map.Equals(TEXT("/Game/WorldRebuild/AegisCitadel_")+Signature.Left(12)+TEXT("/SiegeCandidate"),ESearchCase::CaseSensitive)
        || !ProofString(Proof,TEXT("cityDefinition"),TEXT("/Game/WorldRebuild/AegisCitadel_")+Signature.Left(12)+TEXT("/City"))
        || !Proof->TryGetObjectField(TEXT("definition"),Definition)
        || !ProofString(*Definition,TEXT("id"),TEXT("lower_city")) || !ProofString(*Definition,TEXT("map"),Map)
        || !ProofString(*Definition,TEXT("contentRevision"),Revision) || !ProofNumber(*Definition,TEXT("capacity"),18)
        || !ProofNumber(*Definition,TEXT("rulesVersion"),2) || !ProofString(*Definition,TEXT("battlefield"),TEXT("FullSiege"))
        || !ProofNumber(*Definition,TEXT("gatherMs"),30000) || !ProofNumber(*Definition,TEXT("acceptMs"),30000)
        || !ProofNumber(*Definition,TEXT("reconnectMs"),120000)
        || !ProofString(*Definition,TEXT("name"),TEXT("Siege of Bastion of Aegis"))
        || !ProofString(*Definition,TEXT("description"),TEXT("Breach the city, capture both side objectives and the courtyard, then defeat the commander.")))
    { Error=TEXT("The private candidate queue descriptor is incomplete or changes the existing scenario rules.");return false; }
    return true;
}

bool WarScenarioCandidateProof::Bindings(const TSharedPtr<FJsonObject>& Proof,FString& Error)
{
    if (UE_BUILD_SHIPPING || !Identity(Proof,Error)) return false;
    FString CandidatePath,BlueprintPath,BinaryPath,Hash;
    const FString Revision=Proof->GetStringField(TEXT("signature")).Left(12);
    const FString Directory=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("../../artifacts/unreal/aegis-citadel")/Revision);
    const auto BoundFile=[&](const TCHAR* Name,const TCHAR* HashName,const FString& Expected,FString& Filename)
    {
        return Proof->TryGetStringField(Name,Filename) && FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(Filename),Expected)
            && Proof->TryGetStringField(HashName,Hash) && SameFileHash(Filename,Hash,Error);
    };
    if (!BoundFile(TEXT("candidateReceiptPath"),TEXT("candidateReceiptSha256"),Directory/TEXT("candidate.json"),CandidatePath)
        || !BoundFile(TEXT("blueprintPath"),TEXT("blueprintSha256"),Directory/TEXT("blueprint.json"),BlueprintPath)
        || !BoundFile(TEXT("binaryPath"),TEXT("binarySha256"),FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("Binaries/Win64/UnrealEditor-AegisWar.dll")),BinaryPath)
        || !FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(BinaryPath),FPaths::ConvertRelativePathToFull(FModuleManager::Get().GetModuleFilename(TEXT("AegisWar")))))
    { Error=TEXT("The exact private queue candidate receipts or loaded Win64 development binary changed.");return false; }
    const auto Receipt=WarScenarioTransport::ReadConfig(CandidatePath),Blueprint=WarScenarioTransport::ReadConfig(BlueprintPath);
    const TSharedPtr<FJsonObject>* City=nullptr;FString Payload;
    if (!Receipt || !Blueprint || !ProofNumber(Receipt,TEXT("schemaVersion"),1) || !ProofBool(Receipt,TEXT("published"),false)
        || !ProofBool(Receipt,TEXT("nativeImported"),true) || !ProofString(Receipt,TEXT("siegeMap"),Proof->GetStringField(TEXT("map")))
        || !ProofString(Receipt,TEXT("signature"),Proof->GetStringField(TEXT("signature"))) || !ProofString(Blueprint,TEXT("signature"),Proof->GetStringField(TEXT("signature")))
        || !ProofString(Receipt,TEXT("revision"),Revision) || !ProofString(Blueprint,TEXT("revision"),Revision)
        || !ProofString(Receipt,TEXT("geometrySignature"),Proof->GetStringField(TEXT("geometrySignature")))
        || !Receipt->TryGetObjectField(TEXT("city"),City) || !ProofString(*City,TEXT("definition"),Proof->GetStringField(TEXT("cityDefinition")))
        || !ProofString(*City,TEXT("revision"),Proof->GetStringField(TEXT("cityRevision"))) || !(*City)->TryGetStringField(TEXT("revisionPayload"),Payload)
        || !WarCitadelProofHash::Text(Payload,Hash,Error) || Hash!=Proof->GetStringField(TEXT("cityRevision")))
    { Error=TEXT("The private queue shared-city or authored candidate identity differs from its actual receipt.");return false; }
    const TSharedPtr<FJsonObject>* Packages=nullptr;auto Union=MakeShared<FJsonObject>();
    for (const auto& Table:TArray<TPair<TSharedPtr<FJsonObject>,FString>>{{Receipt,TEXT("sourceHashes")},{Receipt,TEXT("packageHashes")},{*City,TEXT("dependencyHashes")},{*City,TEXT("packageHashes")}})
    {
        const TSharedPtr<FJsonObject>* Entries=nullptr;
        if (!Table.Key->TryGetObjectField(Table.Value,Entries) || (*Entries)->Values.IsEmpty())
        { Error=TEXT("The candidate queue lacks its preserved or owned package hashes.");return false; }
        for (const auto& Pair:(*Entries)->Values)
        {
            const FString Name(*Pair.Key);FString Expected;
            if (!Pair.Value->TryGetString(Expected) || !ProofHash(Expected) || (Union->HasField(Name) && !ProofString(Union,*Name,Expected)))
            { Error=TEXT("The candidate queue has conflicting package hashes.");return false; }
            Union->SetStringField(Name,Expected);
        }
    }
    if (!Proof->TryGetObjectField(TEXT("packageHashes"),Packages) || Union->Values.Num()>4096 || !SameHashMap(Union,*Packages)
        || !ProofString(*Packages,*Proof->GetStringField(TEXT("map")),Proof->GetStringField(TEXT("mapSha256"))))
    { Error=TEXT("The candidate queue package ownership set differs from its actual native receipt.");return false; }
    for (const auto& Pair:(*Packages)->Values)
    {
        const FString Name(*Pair.Key);FString Filename,Expected;
        if (!(Name.StartsWith(TEXT("/Game/")) || Name.StartsWith(TEXT("/Engine/"))) || !FPackageName::IsValidLongPackageName(Name,true)
            || !FPackageName::DoesPackageExist(Name,&Filename) || !Pair.Value->TryGetString(Expected) || !SameFileHash(Filename,Expected,Error))
        { Error=TEXT("A preserved or owned native queue package is missing or changed.");return false; }
    }
    const TSharedPtr<FJsonObject>* Sources=nullptr;const FString SourceRoot=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("Source"));
    if (!Proof->TryGetObjectField(TEXT("sourceHashes"),Sources) || (*Sources)->Values.IsEmpty() || (*Sources)->Values.Num()>1024)
    { Error=TEXT("The candidate queue needs its complete bounded native source set.");return false; }
    TSet<FString> BoundSources;bool InstanceBound=false,MenuBound=false;
    for (const auto& Pair:(*Sources)->Values)
    {
        const FString Filename=FPaths::ConvertRelativePathToFull(FString(*Pair.Key));const FString Extension=FPaths::GetExtension(Filename).ToLower();FString Expected;
        if (!FPaths::IsUnderDirectory(Filename,SourceRoot) || (Extension!=TEXT("cpp") && Extension!=TEXT("h") && Extension!=TEXT("cs"))
            || !Pair.Value->TryGetString(Expected) || !SameFileHash(Filename,Expected,Error))
        { Error=TEXT("The bound native queue source changed or escaped its project.");return false; }
        FString Normal=Filename;FPaths::NormalizeFilename(Normal);Normal=Normal.ToLower();
        if (BoundSources.Contains(Normal)) { Error=TEXT("Duplicate native queue source identity.");return false; }BoundSources.Add(Normal);
        InstanceBound|=Normal.EndsWith(TEXT("/aegiswar/private/warscenarioinstance.cpp"));MenuBound|=Normal.EndsWith(TEXT("/aegiswar/private/warscenariomenuproof.cpp"));
    }
    TArray<FString> NativeFiles;IFileManager::Get().FindFilesRecursive(NativeFiles,*SourceRoot,TEXT("*"),true,false);
    TSet<FString> ActualSources;
    for (FString Filename:NativeFiles)
    {
        const FString Extension=FPaths::GetExtension(Filename).ToLower();if (Extension!=TEXT("cpp") && Extension!=TEXT("h") && Extension!=TEXT("cs")) continue;
        FPaths::NormalizeFilename(Filename);ActualSources.Add(Filename.ToLower());
    }
    if (!InstanceBound || !MenuBound || ActualSources.Num()!=BoundSources.Num())
    { Error=TEXT("The private candidate source receipt omits native project files.");return false; }
    for (const FString& Filename:ActualSources) if (!BoundSources.Contains(Filename))
    { Error=TEXT("The private candidate source receipt omits a native project file.");return false; }
    return true;
}

bool WarScenarioCandidateProof::Battlefield(const TSharedPtr<FJsonObject>& Proof,const AWarSiegeBattlefield* Field,FString& Error,const TSharedPtr<FJsonObject>& SignedBlueprint)
{
    if (UE_BUILD_SHIPPING || !Identity(Proof,Error) || !Field || !Field->GetWorld() || !Field->CityDefinition
        || UWorld::RemovePIEPrefix(Field->GetWorld()->GetOutermost()->GetName())!=Proof->GetStringField(TEXT("map"))
        || Field->GetLevel()!=Field->GetWorld()->PersistentLevel || Field->bLiveCapitalOverlay || Field->DefinitionVersion!=2
        || Field->Capital!=TEXT("aegis_capital") || Field->CityDefinition->ZoneId!=TEXT("aegis_capital")
        || Field->CityDefinition->GetOutermost()->GetName()!=Proof->GetStringField(TEXT("cityDefinition"))
        || Field->CityDefinition->Revision!=Proof->GetStringField(TEXT("cityRevision")))
    { Error=TEXT("The actual queued battlefield is not the exact private candidate shared-city revision.");return false; }
    const auto Blueprint=SignedBlueprint ? SignedBlueprint : WarScenarioTransport::ReadConfig(Proof->GetStringField(TEXT("blueprintPath")));
    const auto Anchors=[&](const TCHAR* Key,const TArray<FVector>& Actual)
    {
        const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;if (!Blueprint || !Blueprint->TryGetArrayField(Key,Rows) || Rows->Num()!=Actual.Num()) return false;
        for (int32 I=0;I<Actual.Num();++I)
        {
            const TArray<TSharedPtr<FJsonValue>>* Coordinates=nullptr;
            if (!(*Rows)[I]->TryGetArray(Coordinates) || Coordinates->Num()!=3) return false;
            FVector Point;
            for (int32 Axis=0;Axis<3;++Axis) if ((*Coordinates)[Axis]->Type!=EJson::Number || !(*Coordinates)[Axis]->TryGetNumber(Point[Axis]) || !FMath::IsFinite(Point[Axis])) return false;
            if (!Actual[I].Equals(Point,.1)) return false;
        }
        return true;
    };
    if (Field->Objectives.Num()!=8 || Field->OptionalObjectives.Num()!=3 || Field->TeamSpawns.Num()!=6
        || !Anchors(TEXT("objectives"),Field->Objectives) || !Anchors(TEXT("optionalObjectives"),Field->OptionalObjectives)
        || !Anchors(TEXT("teamSpawns"),Field->TeamSpawns))
    { Error=TEXT("The actual queued objective or spawn anchors differ from the signed private geometry.");return false; }
    return true;
}

void UWarScenarioInstance::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);FString File;
    if (!UE_BUILD_SHIPPING && IsRunningDedicatedServer() && FParse::Value(FCommandLine::Get(),TEXT("WarScenarioInstance="),File))
    {
        Config=WarScenarioTransport::ReadConfig(File);
        FString Key,Match,Url;
        if (!Config || !Config->TryGetStringField(TEXT("key"),Key) || Key.Len()<32 || !Config->TryGetStringField(TEXT("match"),Match)
            || !Config->TryGetStringField(TEXT("url"),Url) || !Url.StartsWith(TEXT("http://127.0.0.1:")))
        { Config.Reset();UE_LOG(LogTemp,Error,TEXT("WAR_SIEGE_CONTENT_BLOCKED invalid instance allocation")); }
        const bool CandidateFlag=FParse::Param(FCommandLine::Get(),TEXT("WarScenarioCandidateProof"));
        if (CandidateFlag || (Config && Config->HasField(TEXT("candidateProof"))))
        {
            const TSharedPtr<FJsonObject>* Descriptor=nullptr;FString MultiHome;
            bool Safe=Config && CandidateFlag && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking"))
                && Config->TryGetObjectField(TEXT("candidateProof"),Descriptor) && WarScenarioCandidateProof::Identity(*Descriptor,CandidateError)
                && ProofGuid(Match) && ProofBool(Config,TEXT("allowLan"),false)
                && FParse::Value(FCommandLine::Get(),TEXT("MULTIHOME="),MultiHome) && MultiHome==TEXT("127.0.0.1");
            if (Safe)
            {
                Safe=WarScenarioCandidateProof::LoopbackUrl(Url);
                Safe&=FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(File),ScenarioProofRoot(*Descriptor)/TEXT("instances")/Match/TEXT("instance.json"))
                    && ProofNumber(Config,TEXT("capacity"),18) && ProofNumber(Config,TEXT("rulesVersion"),2)
                    && ProofString(Config,TEXT("battlefield"),TEXT("FullSiege"))
                    && ProofString(Config,TEXT("contentRevision"),(*Descriptor)->GetStringField(TEXT("cityRevision")));
                const auto Saved=WarScenarioTransport::ReadConfig(ScenarioProofRoot(*Descriptor)/TEXT("candidate-proof.json"));
                Safe&=Saved && FJsonValue::CompareEqual(FJsonValueObject(Saved),FJsonValueObject(*Descriptor));
                if (Safe) Safe=WarScenarioCandidateProof::Bindings(*Descriptor,CandidateError);
            }
            if (Safe) { CandidateProof=*Descriptor;CandidateBlueprint=WarScenarioTransport::ReadConfig(CandidateProof->GetStringField(TEXT("blueprintPath"))); }
            else
            {
                Config.Reset();if (CandidateError.IsEmpty()) CandidateError=TEXT("Candidate queue override requires an isolated loopback proof allocation and exact saved descriptor.");
                UE_LOG(LogTemp,Error,TEXT("WAR_SIEGE_CONTENT_BLOCKED %s"),*CandidateError);
            }
        }
    }
}
TStatId UWarScenarioInstance::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarScenarioInstance,STATGROUP_Tickables); }
bool UWarScenarioInstance::AllowsLan() const { bool Value=false;return Config && Config->TryGetBoolField(TEXT("allowLan"),Value) && Value; }
void UWarScenarioInstance::Send(const FString& Path,TSharedPtr<FJsonObject> Body,TFunction<void(bool,TSharedPtr<FJsonObject>,FString)> Reply)
{
    if (!Config) { Reply(false,nullptr,TEXT("Instance is not allocated."));return; }
    Body->SetStringField(TEXT("match"),Config->GetStringField(TEXT("match")));
    WarScenarioTransport::Request(Config->GetStringField(TEXT("url")),Config->GetStringField(TEXT("key")),TEXT("POST"),Path,Body,MoveTemp(Reply));
}
void UWarScenarioInstance::Admit(const FString& Ticket,TFunction<void(FString)> Complete)
{
    if (CandidateProof)
    {
        AWarSiegeBattlefield* Field=nullptr;
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld());It;++It)
        { if (Field) { Complete(TEXT("Duplicate candidate queue battlefield."));return; }Field=*It; }
        FString Error;if (!ReviewCandidate(Field,Error,true)) { Complete(Error);return; }
    }
    if (Ticket.Len()!=64 || InFlight.Contains(Ticket) || Pending.Contains(Ticket)) { Complete(TEXT("Missing or duplicate scenario admission ticket."));return; }
    InFlight.Add(Ticket);auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("ticket"),Ticket);
    const TWeakObjectPtr<UWarScenarioInstance> Weak=this;
    Send(TEXT("/instance/consume"),Body,[Weak,Ticket,Complete=MoveTemp(Complete)](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) mutable {
        if (auto* Self=Weak.Get()) {
            Self->InFlight.Remove(Ticket);
            if (Ok) { Self->Pending.Add(Ticket,Data);Self->PendingAt.Add(Ticket,FPlatformTime::Seconds()); }
            Complete(Ok ? FString() : Error);
        } else Complete(TEXT("Scenario instance closed."));
    });
}
bool UWarScenarioInstance::Attach(AWarPlayerController* PC,const FString& Ticket,FString& Error)
{
    auto* Data=Pending.Find(Ticket);
    if (!Data || !WarScenarioTransport::Restore(PC,*Data,true,Error)) { Error=TEXT("Scenario character could not be restored: ")+Error;return false; }
    const FString Id=(*Data)->GetStringField(TEXT("id"));
    for (const auto& Pair:Players) if (Pair.Key.IsValid() && Pair.Value==Id) { Error=TEXT("Character already has a scenario connection.");return false; }
    Players.Add(PC,Id);Pending.Remove(Ticket);PendingAt.Remove(Ticket);
    if (FirstPlayerAt==0) FirstPlayerAt=FPlatformTime::Seconds();
    return true;
}
void UWarScenarioInstance::Disconnect(AWarPlayerController* PC)
{
    FString Id;if (!Players.RemoveAndCopyValue(PC,Id)) return;
    auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("id"),Id);
    Send(TEXT("/instance/disconnect"),Body,[](bool,TSharedPtr<FJsonObject>,FString){});
}
bool UWarScenarioInstance::CanStart(int32 Humans) const
{
    if (Humans<1 || !Roster) return false;
    for (const auto& Value:Roster->GetArrayField(TEXT("members")))
        if (Value->AsObject()->GetStringField(TEXT("phase"))==TEXT("travel") && FPlatformTime::Seconds()-FirstPlayerAt<120) return false;
    return true;
}
void UWarScenarioInstance::Finish()
{
    if (bFinished || !Config) return;bFinished=true;
    for (const auto& Pair:Players) if (auto* PC=Pair.Key.Get())
        if (APawn* Pawn=PC->GetPawn()) { PC->UnPossess();Pawn->Destroy(); }
    Send(TEXT("/instance/finish"),MakeShared<FJsonObject>(),[](bool,TSharedPtr<FJsonObject>,FString){});
}
void UWarScenarioInstance::Tick(float Delta)
{
    if (LastHeartbeat==0) LastHeartbeat=FPlatformTime::Seconds();
    if (Config && !bFinished && FPlatformTime::Seconds()-LastHeartbeat>15)
    {
        Finish();FPlatformMisc::RequestExit(false);return;
    }
    if (!Config || bPolling || FPlatformTime::Seconds()<NextPoll) return;
    NextPoll=FPlatformTime::Seconds()+1;bPolling=true;
    TArray<FString> Expired;
    for (const auto& Pair:PendingAt) if (FPlatformTime::Seconds()-Pair.Value>15) Expired.Add(Pair.Key);
    for (const auto& Ticket:Expired)
    {
        auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("id"),Pending[Ticket]->GetStringField(TEXT("id")));
        Send(TEXT("/instance/disconnect"),Body,[](bool,TSharedPtr<FJsonObject>,FString){});Pending.Remove(Ticket);PendingAt.Remove(Ticket);
    }
    const TWeakObjectPtr<UWarScenarioInstance> Weak=this;
    Send(TEXT("/instance/roster"),MakeShared<FJsonObject>(),[Weak](bool Ok,TSharedPtr<FJsonObject> Data,FString) {
        auto* Self=Weak.Get();if (!Self) return;Self->bPolling=false;if (!Ok) return;Self->Roster=Data;Self->LastHeartbeat=FPlatformTime::Seconds();
        if (Data->GetStringField(TEXT("phase"))==TEXT("finished")) { Self->Finish();FPlatformMisc::RequestExit(false);return; }
        TArray<AWarPlayerController*> Released;
        for (const auto& Value:Data->GetArrayField(TEXT("members")))
        {
            const auto Member=Value->AsObject();if (Member->GetStringField(TEXT("phase"))!=TEXT("return")) continue;
            const FString Id=Member->GetStringField(TEXT("id"));bool bOwned=false;
            for (const auto& Pair:Self->Players) if (Pair.Key.IsValid() && Pair.Value==Member->GetStringField(TEXT("id")))
            {
                auto* PC=Pair.Key.Get();if (APawn* Pawn=PC->GetPawn()) { PC->UnPossess();Pawn->Destroy(); }
                Released.AddUnique(PC);bOwned=true;
            }
            bool bAdmissionPending=!Self->InFlight.IsEmpty();
            for (const auto& Pair:Self->Pending) bAdmissionPending |= Pair.Value->GetStringField(TEXT("id"))==Id;
            // A lost admission response may consume the ticket without creating a pawn.
            // Confirm that absence too, so campaign recovery cannot wait forever.
            if (!bOwned && !bAdmissionPending) {
                auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("id"),Id);
                Self->Send(TEXT("/instance/disconnect"),Body,[](bool,TSharedPtr<FJsonObject>,FString){});
            }
        }
        for (auto* PC:Released) Self->Disconnect(PC);
    });
}

int32 UWarScenarioInstance::RulesVersion() const
{ double Number = 1; if (Config) Config->TryGetNumberField(TEXT("rulesVersion"), Number); return int32(Number); }
int32 UWarScenarioInstance::Capacity() const
{ double Number = 6; if (Config) Config->TryGetNumberField(TEXT("capacity"), Number); return int32(Number); }
EWarSiegeScenario UWarScenarioInstance::Scenario() const
{ FString Name; if (Config) Config->TryGetStringField(TEXT("battlefield"), Name); return Name == TEXT("FullSiege") ? EWarSiegeScenario::FullSiege : EWarSiegeScenario::LowerCity; }
FString UWarScenarioInstance::ContentRevision() const
{ FString Revision; if (Config) Config->TryGetStringField(TEXT("contentRevision"), Revision); return Revision; }

bool UWarScenarioInstance::ReviewCandidate(AWarSiegeBattlefield* Field,FString& Error,bool Recheck)
{
    if (!CandidateError.IsEmpty()) { Error=CandidateError;return false; }
    if (!CandidateProof) return true;
    if (!Config || UE_BUILD_SHIPPING || !IsRunningDedicatedServer() || !FParse::Param(FCommandLine::Get(),TEXT("WarScenarioCandidateProof")))
    { Error=TEXT("The private candidate review cannot be used by an ordinary scenario host.");return false; }
    if (Recheck)
    {
        const auto Saved=WarScenarioTransport::ReadConfig(ScenarioProofRoot(CandidateProof)/TEXT("candidate-proof.json"));
        if (!Saved || !FJsonValue::CompareEqual(FJsonValueObject(Saved),FJsonValueObject(CandidateProof))
            || !WarScenarioCandidateProof::Bindings(CandidateProof,Error))
        { if (Error.IsEmpty()) Error=TEXT("The private candidate descriptor changed before queue admission.");return false; }
    }
    if (!WarScenarioCandidateProof::Battlefield(CandidateProof,Field,Error,CandidateBlueprint)) return false;
    // Explicitly private and transient: every model/navigation/equipment validation still follows.
    Field->ReviewedCityRevision=CandidateProof->GetStringField(TEXT("cityRevision"));
    Field->bTraversalReviewed=true;Field->bEquippedRosterReviewed=true;
    return true;
}
