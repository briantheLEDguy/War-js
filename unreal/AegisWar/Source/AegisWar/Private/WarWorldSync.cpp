#include "WarWorldSync.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Policies/CondensedJsonPrintPolicy.h"

bool WarWorldSync::PreparePull(const FString& Response, const FString& Map, int32 ExpectedRevision,
    FWarWorldEditHistory& Next, int32& RemoteRevision, FString& Error)
{
    TSharedPtr<FJsonObject> Root;
    const TSharedPtr<FJsonObject>* Data = nullptr;
    FString RemoteMap; double Revision = -1;
    if (Next.GetRevision() != ExpectedRevision)
    { Error = TEXT("Local edits changed during sync. Retry; your edits are retained."); return false; }
    if (FTCHARToUTF8(*Response).Length() > 9000000
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response), Root) || !Root
        || !Root->TryGetObjectField(TEXT("data"), Data) || !Data || !Data->IsValid()
        || !(*Data)->TryGetStringField(TEXT("map"), RemoteMap) || RemoteMap != Map
        || !(*Data)->TryGetNumberField(TEXT("revision"), Revision) || !FMath::IsFinite(Revision)
        || Revision < 0 || Revision >= MAX_int32 || Revision != FMath::FloorToDouble(Revision))
    { Error = TEXT("Invalid remote world response; local edits are retained."); return false; }
    if (Revision == 0)
    {
        const auto Empty = (*Data)->TryGetField(TEXT("document"));
        if (!Empty || !Empty->IsNull()) { Error = TEXT("Invalid empty remote world."); return false; }
    }
    else
    {
        const TSharedPtr<FJsonObject>* Document = nullptr;
        if (!(*Data)->TryGetObjectField(TEXT("document"), Document) || !Document || !Document->IsValid())
        { Error = TEXT("Remote world document is missing."); return false; }
        FString Json;
        FJsonSerializer::Serialize(Document->ToSharedRef(), TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
        if (!Next.ImportDraft(Json, ExpectedRevision, Error)) return false;
    }
    RemoteRevision = static_cast<int32>(Revision);
    return true;
}
