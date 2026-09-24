#include "WarAbilityWorkshopSubsystem.h"
#include "WarAbilityCatalog.h"
#include "WarContentSubsystem.h"
#include "WarDevelopmentAccount.h"
#include "WarPlayerController.h"
#include "WarCharacterVisualDefinition.h"
#include "WarRuntimeSettings.h"
#include "Engine/GameInstance.h"
#include "UObject/UObjectIterator.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

using namespace WarWorkshopJson;
namespace { FString DraftPath() {
    if (!UE_BUILD_SHIPPING && (FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopProof")) || FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopCombatProof")) || FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopDeploymentProof"))))
    { FString Run; FGuid Id; if (FParse::Value(FCommandLine::Get(),TEXT("WarWorkshopRun="),Run) && FGuid::Parse(Run,Id)) return FPaths::ProjectSavedDir()/TEXT("AbilityWorkshopProof")/Id.ToString(EGuidFormats::Digits)/TEXT("draft.json"); }
    return FPaths::ProjectSavedDir()/TEXT("AbilityWorkshop/draft.json"); } }
void UWarAbilityWorkshopSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection); Collection.InitializeDependency<UWarContentSubsystem>(); Collection.InitializeDependency<UWarAbilityCatalog>();
    FString Saved;
    if (FFileHelper::LoadFileToString(Saved,*DraftPath()))
    {
        TSharedPtr<FJsonObject> Recovery;
        if (Saved.Len()<=24000000) FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Saved),Recovery);
        const auto Workspace=Object(Recovery,TEXT("workspace"));
        if (Draft.Load(Workspace ? WarWorkshopJson::Serialize(Workspace) : Saved,Message))
        {
            LastSaved=Saved; SharedBaseline=Object(Recovery,TEXT("baseline")); PendingRequest=Text(Recovery,TEXT("pendingRequest")); PendingAction=Text(Recovery,TEXT("pendingAction"));
            const FString SavedEnvironment=Text(Recovery,TEXT("environment")); if (!SavedEnvironment.IsEmpty()) Environment=SavedEnvironment;
            PendingSerial=MAX_uint64; Message=TEXT("Recovered local draft. Pending operations, if any, can be retried with their original identity.");
        }
        return;
    }
    const auto* Content=GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    if (Draft.Baseline(Content->GetInterfaceCatalogSource(),Message)) Message=TEXT("New draft from the current catalog.");
}
bool UWarAbilityWorkshopSubsystem::SetEnvironment(const FString& Value)
{
    if (!PendingRequest.IsEmpty() || Value.IsEmpty() || Value.Len()>64 || (SharedBaseline && Value!=Environment)) return false;
    for (TCHAR C : Value) if (!FChar::IsLower(C) && !FChar::IsDigit(C) && C!='_' && C!='-') return false;
    if (Environment!=Value) { Versions.Reset(); DeploymentRows.Reset(); ++RemoteChangeSerial; }
    Environment=Value; return true;
}
bool UWarAbilityWorkshopSubsystem::SaveLocal()
{
    if (!Draft.Get()) return false;
    const FString Path=DraftPath(); FString Existing;
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    // Keep an exclusive writer handle across comparison and atomic replacement.
    TUniquePtr<FArchive> Lock(IFileManager::Get().CreateFileWriter(*(Path+TEXT(".lock"))));
    if (!Lock) { Message=TEXT("Another session is saving this local recovery draft."); return false; }
    auto Recovery=MakeShared<FJsonObject>(); Recovery->SetObjectField(TEXT("workspace"),Draft.Get()); if (SharedBaseline) Recovery->SetObjectField(TEXT("baseline"),SharedBaseline);
    Recovery->SetStringField(TEXT("pendingRequest"),PendingRequest); Recovery->SetStringField(TEXT("pendingAction"),PendingAction);
    Recovery->SetStringField(TEXT("environment"),Environment);
    const FString Json=WarWorkshopJson::Serialize(Recovery);
    if (FFileHelper::LoadFileToString(Existing,*Path) && Existing!=LastSaved)
    { Message=TEXT("Local draft changed outside this session. Recover it before saving."); return false; }
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    if (!FFileHelper::SaveStringToFile(Json,*(Path+TEXT(".tmp")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        || !IFileManager::Get().Move(*Path,*(Path+TEXT(".tmp")),true,true,false,true))
    { Message=TEXT("Could not save the local recovery draft."); return false; }
    LastSaved=Json; Message=TEXT("Local recovery draft saved."); return true;
}
void UWarAbilityWorkshopSubsystem::Operation(const FString& Action,const TSharedPtr<FJsonObject>& Body)
{
    if (!PendingRequest.IsEmpty()) { Message=TEXT("Reconcile the pending operation before starting another."); return; }
    auto Envelope=MakeShared<FJsonObject>(); Envelope->SetStringField(TEXT("requestId"),FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
    Envelope->SetStringField(TEXT("action"),Action); Envelope->SetObjectField(TEXT("body"),Body);
    PendingRequest=WarWorkshopJson::Serialize(Envelope); PendingAction=Action; PendingSerial=Draft.Serial();
    if (!SaveLocal()) { PendingRequest.Reset(); PendingAction.Reset(); return; } SendPending();
}
void UWarAbilityWorkshopSubsystem::SendPending()
{
    if (PendingRequest.IsEmpty() || bRequestPending) return;
    bRequestPending=true; Message=TEXT("Saving to shared gateway..."); TWeakObjectPtr<UWarAbilityWorkshopSubsystem> Weak(this);
    GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>()->GatewayRequest(TEXT("POST"),TEXT("operations"),PendingRequest,[Weak](int32 Code,const FString& Body) {
        if (!Weak.IsValid()) return; Weak->bRequestPending=false;
        if (Code==0 || Code>=500) { Weak->Message=TEXT("Connection uncertain. Local changes retained; Retry reuses the same request."); return; }
        if (Code==409)
        { Weak->PendingRequest.Reset(); Weak->SaveLocal(); Weak->Message=TEXT("Conflict: shared draft changed. Local changes retained. Load latest into conflict review."); return; }
        const auto Root=Parse(Body); const auto Data=Object(Root,TEXT("data"));
        if (Code!=200 || !Data) { Weak->PendingRequest.Reset(); Weak->SaveLocal(); Weak->Message=TEXT("Shared operation rejected: ")+Body.Left(1500); return; }
        if (Weak->PendingAction==TEXT("ability.save"))
        {
            Weak->SharedBaseline=Clone(Object(Object(Parse(Weak->PendingRequest),TEXT("body")),TEXT("document")));
            Weak->SharedBaseline->SetNumberField(TEXT("revision"),Number(Data,TEXT("revision")));
            Weak->Draft.AcknowledgeRevision(Number(Data,TEXT("revision"))); Weak->SharedSerial=Weak->PendingSerial; Weak->bSharedAutosave=true;
        }
        Weak->PendingRequest.Reset(); Weak->SaveLocal();
        Weak->Message=Weak->PendingAction==TEXT("ability.publish") ? TEXT("Version saved. Select it in History to deploy.")
            : Weak->PendingAction==TEXT("ability.deploy") ? TEXT("Deployment preparing. Active status requires server acknowledgements.")
            : Weak->PendingSerial==Weak->Draft.Serial() ? TEXT("Shared draft saved.") : TEXT("Shared save acknowledged; newer local edits remain unsaved.");
        Weak->RefreshHistory();
    });
}
void UWarAbilityWorkshopSubsystem::Retry() { SendPending(); }
void UWarAbilityWorkshopSubsystem::Autosave()
{ if (SaveLocal() && bSharedAutosave && PendingRequest.IsEmpty() && !ConflictDocument && SharedSerial!=Draft.Serial()) SaveShared(); }
void UWarAbilityWorkshopSubsystem::SaveShared()
{
    if (!Draft.Get()) return;
    auto Body=MakeShared<FJsonObject>(); Body->SetStringField(TEXT("id"),Text(Draft.Get(),TEXT("id"))); Body->SetStringField(TEXT("environment"),Environment);
    Body->SetNumberField(TEXT("revision"),Number(Draft.Get(),TEXT("revision"))); Body->SetObjectField(TEXT("document"),Clone(Draft.Get())); Operation(TEXT("ability.save"),Body);
}
void UWarAbilityWorkshopSubsystem::LoadShared(const FString& WorkspaceId)
{
    if (!PendingRequest.IsEmpty()) { Message=TEXT("Reconcile the pending operation before loading shared changes."); return; }
    FGuid Id; if (!FGuid::Parse(WorkspaceId,Id)) { Message=TEXT("Enter a valid workspace ID."); return; }
    const FString RequestedEnvironment=Environment;
    TWeakObjectPtr<UWarAbilityWorkshopSubsystem> Weak(this);
    GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>()->GatewayRequest(TEXT("GET"),TEXT("abilities/")+Environment+TEXT("/workspaces/")+WorkspaceId,TEXT(""),[Weak,RequestedEnvironment](int32 Code,const FString& Body) {
        if (!Weak.IsValid() || Weak->Environment!=RequestedEnvironment || !Weak->PendingRequest.IsEmpty()) return; const auto Root=Parse(Body); const auto& Rows=Array(Root,TEXT("data"));
        if (Code!=200 || Rows.IsEmpty()) { Weak->Message=TEXT("Could not read shared workspace: ")+Body.Left(500); return; }
        Weak->ConflictDocument=Object(Rows[0]->AsObject(),TEXT("document"));
        Weak->ConflictChoices.Reset(); Weak->BuildMerge();
        ++Weak->RemoteChangeSerial;
    });
}
void UWarAbilityWorkshopSubsystem::Publish(const FString& Name)
{
    if (!Draft.Get()) return;
    if (SharedSerial!=Draft.Serial()) { Message=TEXT("Save and acknowledge this exact draft before publishing."); return; }
    TArray<FWarAbilityDefinition> Definitions;
    if (!FWarAbilityWorkshopDocument::Compile(Draft.Get(),Definitions,Message) || !ValidatePresentations(Definitions,Message)) return;
    auto Body=MakeShared<FJsonObject>(); Body->SetStringField(TEXT("id"),FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
    Body->SetStringField(TEXT("workspaceId"),Text(Draft.Get(),TEXT("id"))); Body->SetNumberField(TEXT("revision"),Number(Draft.Get(),TEXT("revision"))); Body->SetStringField(TEXT("name"),Name);
    Operation(TEXT("ability.publish"),Body);
}
void UWarAbilityWorkshopSubsystem::BuildMerge()
{
    if (!SharedBaseline || !ConflictDocument || Text(ConflictDocument,TEXT("id"))!=Text(Draft.Get(),TEXT("id")))
    { MergePreview.Reset(); ConflictFields.Reset(); Message=TEXT("No common saved baseline for this workspace. Local draft retained; automatic merge is unavailable."); return; }
    MergePreview=FWarAbilityWorkshopDocument::Merge(SharedBaseline,ConflictDocument,Draft.Get(),ConflictChoices,ConflictFields);
    Message=FString::Printf(TEXT("Merge preview: %d unresolved fields. Choose current or yours, then commit the merged draft."),ConflictFields.Num());
}
void UWarAbilityWorkshopSubsystem::ResolveConflict(const FString& Path,bool bUseYours)
{ ConflictChoices.Add(Path,bUseYours); BuildMerge(); }
void UWarAbilityWorkshopSubsystem::CommitMerge()
{
    BuildMerge(); if (!MergePreview || !ConflictFields.IsEmpty()) return;
    if (!Draft.Commit(MergePreview,Message)) return;
    SharedBaseline=Clone(ConflictDocument); ConflictDocument.Reset(); MergePreview.Reset(); ConflictChoices.Reset(); SharedSerial=MAX_uint64;
    SaveLocal(); Message=TEXT("Merged draft committed locally. Save shared to retry against the current revision.");
}
void UWarAbilityWorkshopSubsystem::Deploy(const FString& VersionId)
{
    FGuid Id; if (!FGuid::Parse(VersionId,Id)) { Message=TEXT("Select a valid version."); return; }
    auto Body=MakeShared<FJsonObject>(); Body->SetStringField(TEXT("id"),FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
    Body->SetStringField(TEXT("versionId"),VersionId); Body->SetStringField(TEXT("environment"),Environment); Operation(TEXT("ability.deploy"),Body);
}
void UWarAbilityWorkshopSubsystem::RefreshHistory()
{
    TWeakObjectPtr<UWarAbilityWorkshopSubsystem> Weak(this);
    const FString RequestedEnvironment=Environment;
    for (const FString Kind : {FString(TEXT("versions")),FString(TEXT("deployments"))})
        GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>()->GatewayRequest(TEXT("GET"),TEXT("abilities/")+Environment+TEXT("/")+Kind,TEXT(""),[Weak,Kind,RequestedEnvironment](int32 Code,const FString& Body) {
            if (!Weak.IsValid() || Code!=200 || Weak->Environment!=RequestedEnvironment) return; const auto Root=Parse(Body);
            if (Kind==TEXT("versions")) Weak->Versions=Array(Root,TEXT("data")); else Weak->DeploymentRows=Array(Root,TEXT("data"));
            ++Weak->RemoteChangeSerial;
        });
}
TSharedPtr<FJsonObject> UWarAbilityWorkshopSubsystem::ReviewBaseline(FString& Version,FString& Error) const
{
    const auto* Catalog=GetGameInstance()->GetSubsystem<UWarAbilityCatalog>(); Version=Catalog->GetVersion();
    if (!Catalog->GetActiveDocument().IsEmpty()) return Parse(Catalog->GetActiveDocument());
    FWarAbilityWorkshopDocument Baseline;
    return Baseline.Baseline(GetGameInstance()->GetSubsystem<UWarContentSubsystem>()->GetInterfaceCatalogSource(),Error) ? Baseline.Get() : nullptr;
}
bool UWarAbilityWorkshopSubsystem::ValidatePresentations(const TArray<FWarAbilityDefinition>& Definitions,FString& Error) const
{
    auto Profiles=GetDefault<UWarRuntimeSettings>()->PlayableRoster;
    Profiles.AddUnique(GetDefault<UWarRuntimeSettings>()->AegisDevelopmentVisual);
    Profiles.AddUnique(GetDefault<UWarRuntimeSettings>()->RiftboundDevelopmentVisual);
    for (const auto& A : Definitions)
    {
        if (!A.UnavailableReason.IsEmpty()) continue;
        bool Found=false;
        for (const auto& Profile : Profiles)
        {
            const auto* It=Profile.LoadSynchronous();
            if (!It || It->ClassId!=A.Career) continue;
            if (!It->ValidateForSpawn(It->Realm,Error)) { Error=A.Name+TEXT(": ")+Error; return false; }
            const FName Binding=WarAbilities::Motion(A,It->ProfileKey);
            const auto* Recipe=It->AbilityPresentations.Find(Binding);
            Found=false;
            if (Recipe && !Recipe->VariantRoles.IsEmpty()) { Found=true; for (FName Role : Recipe->VariantRoles) if (!It->ImportedAnimations.Contains(Role) || !It->ImportedAnimations[Role].LoadSynchronous()) { Found=false; break; } }
            if (!Found) { Error=A.Name+TEXT(": incompatible presentation for ")+It->ProfileKey.ToString(); return false; }
        }
        if (!Found) { Error=A.Name+TEXT(": no loaded, approved presentation for this class. Select a compatible recipe."); return false; }
    }
    return true;
}
