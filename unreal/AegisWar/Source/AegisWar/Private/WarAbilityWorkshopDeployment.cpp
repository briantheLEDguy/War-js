#include "WarAbilityWorkshopSubsystem.h"
#include "WarAbilityCatalog.h"
#include "WarContentSubsystem.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

using namespace WarWorkshopJson;
TStatId UWarAbilityWorkshopSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarAbilityWorkshopSubsystem,STATGROUP_Tickables); }
UWorld* UWarAbilityWorkshopSubsystem::GetTickableGameObjectWorld() const { return GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr; }
void UWarAbilityWorkshopSubsystem::Deinitialize() { PersonalJournal.Reset(); Super::Deinitialize(); }
FString UWarAbilityWorkshopSubsystem::PersonalDirectory() const
{
    if (!UE_BUILD_SHIPPING && (FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopProof")) || FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopDeploymentProof")))) {
        FString Run; FGuid Id;
        if (FParse::Value(FCommandLine::Get(),TEXT("WarWorkshopRun="),Run) && FGuid::Parse(Run,Id)) return FPaths::ProjectSavedDir()/TEXT("AbilityWorkshopProof")/Id.ToString(EGuidFormats::Digits)/TEXT("deployments");
    }
    return FPaths::ProjectSavedDir()/TEXT("AbilityWorkshop/deployments");
}
bool UWarAbilityWorkshopSubsystem::EnsurePersonal(AWarPlayerController* Controller)
{
    if (UE_BUILD_SHIPPING || !Controller || !Controller->IsLocalController() || !Controller->HasAuthority() || !Controller->CanUseGmTools()
        || Controller->GetWorld()->GetNetMode()!=NM_Standalone)
    { Message=TEXT("Personal deployment requires your authorized local GM development session."); return false; }
    if (!PersonalJournal) { auto Journal=MakeUnique<FWarAbilityDeploymentJournal>(); if (!Journal->Open(PersonalDirectory(),Message)) return false; PersonalJournal=MoveTemp(Journal); }
    return true;
}
const TArray<TSharedPtr<FJsonValue>>& UWarAbilityWorkshopSubsystem::PersonalHistory() const
{ static const TArray<TSharedPtr<FJsonValue>> Empty; return PersonalJournal ? PersonalJournal->Records() : Empty; }
bool UWarAbilityWorkshopSubsystem::ValidatePersonal(const TSharedPtr<FJsonObject>& Workspace,FString& Error) const
{
    TArray<FWarAbilityDefinition> Definitions; if (!FWarAbilityWorkshopDocument::Compile(Workspace,Definitions,Error)) return false;
    FWarAbilityWorkshopDocument Shipped;
    if (!Shipped.Baseline(GetGameInstance()->GetSubsystem<UWarContentSubsystem>()->GetInterfaceCatalogSource(),Error)) return false;
    if (Text(Workspace,TEXT("buildId"))!=Text(Shipped.Get(),TEXT("buildId")) || Text(Workspace,TEXT("contentId"))!=Text(Shipped.Get(),TEXT("contentId")))
    { Error=TEXT("This version belongs to another code/content baseline. Rebase the draft before deploying."); return false; }
    TArray<FWarAbilityDefinition> Changed;
    for (const auto& Definition:Definitions) {
        const FString Id=Definition.AssignmentId.ToString();
        const auto Assignment=Find(Workspace,TEXT("assignments"),Id),Original=Find(Shipped.Get(),TEXT("assignments"),Id);
        const auto Effective=FWarAbilityWorkshopDocument::Effective(Workspace,Assignment,Error);
        const auto Baseline=Original ? FWarAbilityWorkshopDocument::Effective(Shipped.Get(),Original,Error) : nullptr;
        if (!Effective || !Baseline || !FJsonValue::CompareEqual(FJsonValueObject(Effective),FJsonValueObject(Baseline))) Changed.Add(Definition);
    }
    // Unchanged shipped assignments keep their existing admission. Every changed assignment
    // must resolve presentations for every admitted playable profile of that class.
    return ValidatePresentations(Changed,Error);
}
bool UWarAbilityWorkshopSubsystem::StagePersonal(const TSharedPtr<FJsonObject>& Workspace,const FString& Version)
{
    if (!GetGameInstance()->GetSubsystem<UWarAbilityCatalog>()->StageWorkspace(WarWorkshopJson::Serialize(Workspace),TEXT("personal-")+Version,Message)) {
        FString Failure; if (!bRestoringPersonal) PersonalJournal->Fail(Message,Failure);
        PersonalStatus=Message; return false;
    }
    PersonalPendingVersion=Version; PersonalDeadline=FPlatformTime::Seconds()+15;
    PersonalStatus=TEXT("Staged for the next simulation tick. Existing casts, statuses and cooldowns retain their state."); ++RemoteChangeSerial; return true;
}
bool UWarAbilityWorkshopSubsystem::ApplyToDevelopment(AWarPlayerController* Controller)
{
    if (!EnsurePersonal(Controller) || PersonalPending() || !ValidatePersonal(Draft.Get(),Message) || !SaveLocal()) return false;
    FString Version; if (!PersonalJournal->Queue(Draft.Get(),TEXT("Workshop draft r")+FString::SanitizeFloat(Number(Draft.Get(),TEXT("revision")),0),Version,Message)) return false;
    bRestoreChecked=true; bRestoringPersonal=false; return StagePersonal(Draft.Get(),Version);
}
bool UWarAbilityWorkshopSubsystem::RollbackPersonal(AWarPlayerController* Controller,const FString& VersionId)
{
    if (!EnsurePersonal(Controller) || PersonalPending()) return false;
    const auto Workspace=PersonalJournal->ReadVersion(VersionId,Message);
    if (!Workspace || !ValidatePersonal(Workspace,Message) || !PersonalJournal->QueueExisting(VersionId,TEXT("Rollback to saved version"),Message)) return false;
    bRestoreChecked=true; bRestoringPersonal=false; return StagePersonal(Workspace,VersionId);
}
bool UWarAbilityWorkshopSubsystem::RestoreShipped(AWarPlayerController* Controller)
{
    if (!EnsurePersonal(Controller) || PersonalPending()) return false;
    FWarAbilityWorkshopDocument Baseline;
    if (!Baseline.Baseline(GetGameInstance()->GetSubsystem<UWarContentSubsystem>()->GetInterfaceCatalogSource(),Message)) return false;
    FString Version; if (!PersonalJournal->Queue(Baseline.Get(),TEXT("Restore shipped abilities"),Version,Message)) return false;
    bRestoreChecked=true; bRestoringPersonal=false; return StagePersonal(Baseline.Get(),Version);
}
void UWarAbilityWorkshopSubsystem::Tick(float Delta)
{
    if (UE_BUILD_SHIPPING || !GetWorld() || !GetWorld()->HasBegunPlay()) return;
    auto* Controller=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    const auto* Pawn=Controller ? Cast<AWarCharacter>(Controller->GetPawn()) : nullptr;
    if (!Pawn || !Pawn->IsVisualReady() || !Controller->CanUseGmTools()) return;
    auto* Catalog=GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    if (!bRestoreChecked) {
        bRestoreChecked=true;
        if (!EnsurePersonal(Controller)) { PersonalStatus=Message; return; }
        if (!PersonalJournal->Active().IsEmpty()) {
            const auto Workspace=PersonalJournal->ReadVersion(PersonalJournal->Active(),Message);
            if (Workspace && ValidatePersonal(Workspace,Message)) { bRestoringPersonal=true; StagePersonal(Workspace,PersonalJournal->Active()); }
            else PersonalStatus=TEXT("Saved deployment could not be restored: ")+Message;
        } else PersonalStatus=TEXT("Personal session uses shipped abilities. Deploy a reviewed draft to change new casts.");
        ++RemoteChangeSerial;
    }
    if (PersonalPendingVersion.IsEmpty()) return;
    if (!Catalog->HasStagedVersion() && Catalog->GetVersion()==TEXT("personal-")+PersonalPendingVersion) {
        if (!bRestoringPersonal && !PersonalJournal->Complete(PersonalPendingVersion,Message)) { PersonalStatus=TEXT("Active in game; saving activation acknowledgement failed. ")+Message; return; }
        PersonalStatus=TEXT("Active in this game: ")+PersonalPendingVersion.Left(8)+TEXT(". New casts use this version; it will restore on your next GM launch.");
        PersonalPendingVersion.Reset(); bRestoringPersonal=false; ++RemoteChangeSerial;
    } else if (FPlatformTime::Seconds()>PersonalDeadline) {
        Catalog->CancelStaged(TEXT("personal-")+PersonalPendingVersion);
        FString Error; if (!bRestoringPersonal) PersonalJournal->Fail(TEXT("No activation acknowledgement from the running catalog."),Error);
        PersonalStatus=TEXT("Deployment failed to activate. The last confirmed version remains saved."); PersonalPendingVersion.Reset(); bRestoringPersonal=false; ++RemoteChangeSerial;
    }
}
