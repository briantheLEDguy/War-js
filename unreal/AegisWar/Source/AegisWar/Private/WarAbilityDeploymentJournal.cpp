#include "WarAbilityDeploymentJournal.h"
#include "WarAbilityWorkshopDocument.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

using namespace WarWorkshopJson;
namespace {
    bool ReadBounded(const FString& Path,FString& Json,int64 Limit)
    { const int64 Size=IFileManager::Get().FileSize(*Path); return Size>=0 && Size<=Limit && FFileHelper::LoadFileToString(Json,*Path); }
}
bool FWarAbilityDeploymentJournal::ValidId(const FString& Value)
{ FGuid Id; return Value.Len()==36 && FGuid::ParseExact(Value,EGuidFormats::DigitsWithHyphensLower,Id); }
FString FWarAbilityDeploymentJournal::Active() const { return Text(State,TEXT("activeVersion")); }
FString FWarAbilityDeploymentJournal::Pending() const { return Text(State,TEXT("pendingVersion")); }
const TArray<TSharedPtr<FJsonValue>>& FWarAbilityDeploymentJournal::Records() const { return Array(State,TEXT("records")); }
bool FWarAbilityDeploymentJournal::Save(const TSharedPtr<FJsonObject>& Candidate,FString& Error)
{
    const FString Path=Folder/TEXT("journal.json");
    if (!WriterLock || !FFileHelper::SaveStringToFile(Serialize(Candidate),*(Path+TEXT(".tmp")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        || !IFileManager::Get().Move(*Path,*(Path+TEXT(".tmp")),true,true,false,true))
    { Error=TEXT("Could not persist the personal deployment journal. No deployment acknowledgement was saved."); return false; }
    State=Candidate; return true;
}
bool FWarAbilityDeploymentJournal::Open(const FString& Directory,FString& Error)
{
    if (WriterLock) return true;
    Folder=Directory; IFileManager::Get().MakeDirectory(*(Folder/TEXT("versions")),true);
    WriterLock.Reset(IFileManager::Get().CreateFileWriter(*(Folder/TEXT("session.lock"))));
    if (!WriterLock) { Error=TEXT("Another game session owns personal ability deployments. Close that session before deploying here."); return false; }
    const FString Path=Folder/TEXT("journal.json");
    if (IFileManager::Get().FileExists(*Path)) {
        FString Json; State=ReadBounded(Path,Json,2000000) ? Parse(Json) : nullptr;
        if (!State || Number(State,TEXT("schemaVersion"))!=1 || !State->HasTypedField<EJson::Array>(TEXT("records"))
            || (!Active().IsEmpty() && !ValidId(Active())) || (!Pending().IsEmpty() && !ValidId(Pending())))
        { WriterLock.Reset(); Error=TEXT("Personal deployment journal is invalid. Existing files were retained."); return false; }
        for (const auto& Value:Records()) {
            const auto Row=Value && Value->Type==EJson::Object ? Value->AsObject() : nullptr;
            const FString Phase=Text(Row,TEXT("phase"));
            if (!Row || !ValidId(Text(Row,TEXT("versionId"))) || (Phase!=TEXT("staged") && Phase!=TEXT("active") && Phase!=TEXT("failed")))
            { WriterLock.Reset(); Error=TEXT("Personal deployment history is invalid. Existing files were retained."); return false; }
        }
        if (!Pending().IsEmpty() && (Records().IsEmpty() || Text(Records()[0]->AsObject(),TEXT("versionId"))!=Pending()))
        { WriterLock.Reset(); Error=TEXT("Personal deployment pending identity does not match its history."); return false; }
        if (!Pending().IsEmpty() && !Fail(TEXT("Previous session ended before activation was acknowledged. The last confirmed version is retained."),Error)) { WriterLock.Reset(); return false; }
    } else { State=Parse(TEXT(R"({"schemaVersion":1,"activeVersion":"","pendingVersion":"","records":[]})")); }
    return true;
}
TSharedPtr<FJsonObject> FWarAbilityDeploymentJournal::ReadVersion(const FString& Version,FString& Error) const
{
    if (!ValidId(Version)) { Error=TEXT("Invalid personal version identity."); return nullptr; }
    FString Json; const auto Envelope=ReadBounded(Folder/TEXT("versions")/(Version+TEXT(".json")),Json,32000000) ? Parse(Json) : nullptr;
    const auto Document=Object(Envelope,TEXT("document")); TArray<FWarAbilityDefinition> Definitions;
    if (!Envelope || Text(Envelope,TEXT("id"))!=Version || !Document || !FWarAbilityWorkshopDocument::Compile(Document,Definitions,Error))
    { if (Error.IsEmpty()) Error=TEXT("Saved version is missing or invalid. The active catalog was not changed."); return nullptr; }
    return Document;
}
bool FWarAbilityDeploymentJournal::Queue(const TSharedPtr<FJsonObject>& Document,const FString& Name,FString& Version,FString& Error)
{
    TArray<FWarAbilityDefinition> Definitions;
    if (!WriterLock || !Pending().IsEmpty()) { Error=TEXT("A deployment is pending or this session does not own the journal."); return false; }
    if (!FWarAbilityWorkshopDocument::Compile(Document,Definitions,Error)) return false;
    Version=FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
    auto Envelope=MakeShared<FJsonObject>(); Envelope->SetStringField(TEXT("id"),Version); Envelope->SetStringField(TEXT("name"),Name.Left(80));
    Envelope->SetStringField(TEXT("createdAt"),FDateTime::UtcNow().ToIso8601()); Envelope->SetObjectField(TEXT("document"),Clone(Document));
    const FString Path=Folder/TEXT("versions")/(Version+TEXT(".json"));
    if (IFileManager::Get().FileExists(*Path) || !FFileHelper::SaveStringToFile(Serialize(Envelope),*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
    { Error=TEXT("Could not save an immutable personal version."); return false; }
    return QueueExisting(Version,Name,Error);
}
bool FWarAbilityDeploymentJournal::QueueExisting(const FString& Version,const FString& Name,FString& Error)
{
    if (!WriterLock || !Pending().IsEmpty()) { Error=TEXT("A deployment is already pending."); return false; }
    if (!ReadVersion(Version,Error)) return false;
    auto Candidate=Clone(State); auto Record=MakeShared<FJsonObject>();
    Record->SetStringField(TEXT("id"),FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower)); Record->SetStringField(TEXT("versionId"),Version);
    Record->SetStringField(TEXT("name"),Name.Left(80)); Record->SetStringField(TEXT("previousVersion"),Active()); Record->SetStringField(TEXT("phase"),TEXT("staged")); Record->SetStringField(TEXT("createdAt"),FDateTime::UtcNow().ToIso8601());
    auto Rows=Records(); Rows.Insert(MakeShared<FJsonValueObject>(Record),0); if (Rows.Num()>200) Rows.SetNum(200);
    Candidate->SetArrayField(TEXT("records"),Rows); Candidate->SetStringField(TEXT("pendingVersion"),Version);
    return Save(Candidate,Error);
}
bool FWarAbilityDeploymentJournal::Complete(const FString& Version,FString& Error)
{
    if (!ValidId(Version) || Pending()!=Version || Records().IsEmpty()) { Error=TEXT("Deployment acknowledgement does not match the staged version."); return false; }
    auto Candidate=Clone(State); Candidate->SetStringField(TEXT("activeVersion"),Version); Candidate->SetStringField(TEXT("pendingVersion"),TEXT(""));
    Array(Candidate,TEXT("records"))[0]->AsObject()->SetStringField(TEXT("phase"),TEXT("active"));
    return Save(Candidate,Error);
}
bool FWarAbilityDeploymentJournal::Fail(const FString& Reason,FString& Error)
{
    if (Pending().IsEmpty()) { Error=TEXT("No staged deployment to fail."); return false; }
    auto Candidate=Clone(State); Candidate->SetStringField(TEXT("pendingVersion"),TEXT(""));
    if (!Records().IsEmpty()) { const auto Row=Array(Candidate,TEXT("records"))[0]->AsObject(); Row->SetStringField(TEXT("phase"),TEXT("failed")); Row->SetStringField(TEXT("detail"),Reason.Left(500)); }
    return Save(Candidate,Error);
}
