#include "WarWorldEditSubsystem.h"
#include "WarWorldEditStorage.h"
#include "WarWorldSync.h"
#include "WarDevelopmentAccount.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Policies/CondensedJsonPrintPolicy.h"

namespace
{
    FString JsonText(const TSharedRef<FJsonObject>& Value)
    {
        FString Text;
        FJsonSerializer::Serialize(Value, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
        return Text;
    }
}

void UWarWorldEditSubsystem::SyncRemote(APlayerController* Controller, const bool bPublish)
{
    FString Error;
    if (bRemoteBusy) return;
    if (!Ready(Controller, Error)) { RemoteStatus = Error; return; }
    auto* Account = GetWorld()->GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>();
    if (!Account || !Account->IsApproved())
    { RemoteStatus = TEXT("Sign in with an approved developer account before syncing."); return; }
    const FString Map = UWorld::RemovePIEPrefix(GetWorld()->GetOutermost()->GetName());
    const FString Scope = FPlatformMisc::GetEnvironmentVariable(TEXT("AEGIS_DEV_GATEWAY_URL")) + TEXT("|") + Account->GetAccountId() + TEXT("|") + Map;
    if (Scope != RemoteScope)
    { RemoteScope = Scope; RemoteRevision = INDEX_NONE; PendingRemoteRequest.Empty(); }
    if (!bPublish && !PendingRemoteRequest.IsEmpty())
    { RemoteStatus = TEXT("A publication has an uncertain result. Retry Publish remote first to reconcile it."); return; }
    if (bPublish && RemoteRevision == INDEX_NONE)
    { RemoteStatus = TEXT("Pull remote first to check its current revision. Your local draft will be backed up."); return; }
    const int32 LocalRevision = History.GetRevision();
    auto Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("action"), bPublish ? TEXT("publish") : TEXT("read"));
    Body->SetStringField(TEXT("map"), Map);
    if (bPublish && PendingRemoteRequest.IsEmpty())
    {
        TSharedPtr<FJsonObject> Document;
        const FString Draft = History.ExportDraft();
        auto Validate = History;
        if (!Validate.ImportDraft(Draft, LocalRevision, Error)
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Draft), Document))
        { RemoteStatus = Error; return; }
        Body->SetObjectField(TEXT("document"), Document);
        Body->SetNumberField(TEXT("revision"), RemoteRevision);
        Body->SetStringField(TEXT("requestId"), FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
    }
    // Keep recovery snapshots separate from the user's existing named draft/publication.
    if (!bPublish || PendingRemoteRequest.IsEmpty())
    {
        const FString Backup = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("WorldEdit/SyncRecovery"),
            FGuid::NewGuid().ToString(EGuidFormats::Digits) + TEXT(".json"));
        if (!WarWorldEditStorage::Publish(Backup, TEXT(""), History.ExportDraft(), Error))
        { RemoteStatus = TEXT("Sync stopped: could not back up the local world. ") + Error; return; }
    }
    if (bPublish && PendingRemoteRequest.IsEmpty()) PendingRemoteRequest = JsonText(Body);
    const int32 ExpectedRemote = RemoteRevision;
    bRemoteBusy = true;
    RemoteStatus = bPublish ? TEXT("Publishing remote world snapshot...") : TEXT("Pulling remote world; local recovery saved...");
    TWeakObjectPtr<UWarWorldEditSubsystem> Weak(this);
    TWeakObjectPtr<APlayerController> Player(Controller);
    Account->GatewayRequest(TEXT("POST"), TEXT("world-sync"), bPublish ? PendingRemoteRequest : JsonText(Body),
        [Weak, Player, Map, Scope, LocalRevision, ExpectedRemote, bPublish](int32 Code, const FString& Response) {
        if (!Weak.IsValid()) return;
        Weak->bRemoteBusy = false;
        if (Scope != Weak->RemoteScope) return;
        if (Code != 200)
        {
            // Only definitive client rejection clears a publish receipt. Timeouts and
            // server errors retry the identical captured document and request UUID.
            if (bPublish && Code >= 400 && Code < 500 && Code != 401 && Code != 408 && Code != 429)
            { Weak->PendingRemoteRequest.Empty(); Weak->RemoteRevision = INDEX_NONE; }
            Weak->RemoteStatus = Code == 409 ? TEXT("Remote world changed. Pull remote before publishing again; your edits are retained in recovery.")
                : Code == 401 || Code == 403 ? TEXT("Remote access denied. Check sign-in and owner approval; local edits are retained.")
                : TEXT("Remote sync failed. Check the gateway. Retry Publish remote to reconcile an uncertain publication.");
            return;
        }
        FString Failure;
        if (bPublish)
        {
            TSharedPtr<FJsonObject> Root;
            const TSharedPtr<FJsonObject>* Data = nullptr;
            FString RemoteMap; double Revision = -1;
            if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response), Root) || !Root
                || !Root->TryGetObjectField(TEXT("data"), Data) || !Data || !Data->IsValid()
                || !(*Data)->TryGetStringField(TEXT("map"), RemoteMap) || RemoteMap != Map
                || !(*Data)->TryGetNumberField(TEXT("revision"), Revision) || Revision != ExpectedRemote + 1)
            { Weak->RemoteStatus = TEXT("Invalid publication acknowledgement. Retry Publish remote with the same request."); return; }
            Weak->RemoteRevision = static_cast<int32>(Revision); Weak->PendingRemoteRequest.Empty();
            Weak->RemoteStatus = FString::Printf(TEXT("Remote revision %d saved. Runtime deployment is not available; later local edits remain unpublished."), Weak->RemoteRevision);
            return;
        }
        auto Next = Weak->History; int32 Revision = INDEX_NONE;
        if (!Player.IsValid() || !Weak->Ready(Player.Get(), Failure)
            || !WarWorldSync::PreparePull(Response, Map, LocalRevision, Next, Revision, Failure)
            || (Revision > 0 && !Weak->ApplyHistory(MoveTemp(Next), Failure)))
        { Weak->RemoteStatus = Failure.IsEmpty() ? TEXT("Session changed; remote world was not applied.") : Failure; return; }
        Weak->RemoteRevision = Revision;
        Weak->RemoteStatus = Revision == 0 ? TEXT("No remote world published yet. Local draft retained; the owner can publish it.")
            : FString::Printf(TEXT("Synced remote revision %d into the GM world. Undo restores local edits; recovery is saved. Publish locally to retain this layout next launch."), Revision);
    });
}
