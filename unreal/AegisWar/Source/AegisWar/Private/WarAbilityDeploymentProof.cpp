#include "WarAbilityDeploymentProof.h"
#include "WarAbilityWorkshopSubsystem.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityRuntime.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCombatStatus.h"
#include "AbilitySystemComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/PlatformMisc.h"

using namespace WarWorkshopJson;
namespace {
    const FName AbilityId(TEXT("workshop.personal_heal"));
    FString ProofFolder() {
        FString Run; FGuid Id;
        if (!FParse::Value(FCommandLine::Get(),TEXT("WarWorkshopRun="),Run) || !FGuid::Parse(Run,Id)) return {};
        return FPaths::ProjectSavedDir()/TEXT("AbilityWorkshopProof")/Id.ToString(EGuidFormats::Digits);
    }
    bool IsRestart() { return FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopRestart")); }
}
bool UWarAbilityDeploymentProof::ShouldCreateSubsystem(UObject* Outer) const
{ return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopDeploymentProof")) && !ProofFolder().IsEmpty(); }
TStatId UWarAbilityDeploymentProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarAbilityDeploymentProof,STATGROUP_Tickables); }
bool UWarAbilityDeploymentProof::Check(bool Passed,const FString& Label)
{ if (!Passed) { Finish(false,Label); return false; } Checks.Add(Label); return true; }
void UWarAbilityDeploymentProof::Finish(bool Passed,const FString& Detail)
{
    bFinished=true; auto Report=MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"),Passed); Report->SetStringField(TEXT("detail"),Detail);
    TArray<TSharedPtr<FJsonValue>> Rows; for (const auto& C:Checks) Rows.Add(MakeShared<FJsonValueString>(C)); Report->SetArrayField(TEXT("checks"),Rows);
    FFileHelper::SaveStringToFile(WarWorkshopJson::Serialize(Report),*(ProofFolder()/(IsRestart() ? TEXT("restart.json") : TEXT("deployment.json"))));
    UE_LOG(LogTemp,Display,TEXT("WAR_PERSONAL_DEPLOYMENT %s %s"),Passed ? TEXT("passed") : TEXT("FAILED"),*Detail);
    FPlatformMisc::RequestExit(false);
}
void UWarAbilityDeploymentProof::Tick(float Delta)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds(); if (Now<Next) return;
    if (Now>90) { Finish(false,TEXT("Timed out waiting for personal deployment")); return; }
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()); auto* Pawn=PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* State=PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!Pawn || !State || !Pawn->IsVisualReady()) return;
    auto* Store=GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityWorkshopSubsystem>();
    auto* Catalog=GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    auto* Runtime=State->GetClassAbilities(); auto* ASC=State->GetAbilitySystemComponent(); FString Error;
    if (Store->PersonalPending() || Store->DeploymentStatus().IsEmpty()) return;
    const auto Seed=[&] { Runtime->Interrupt(); UWarCombatStatus::On(Pawn)->Clear(); Runtime->ResetCooldowns(); Runtime->RestoreResource(); ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),600); ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),10); };
    if (Step==0) {
        if (!Check(PC->CanUseGmTools() && PC->HasAuthority() && GetWorld()->GetNetMode()==NM_Standalone,TEXT("Ordinary local GM authorization is required"))) return;
        if (IsRestart()) {
            if (!Check(Catalog->GetVersion().StartsWith(TEXT("personal-")) && Catalog->Find(AbilityId,Pawn->GetCareerId()),TEXT("Last confirmed personal version restores on a fresh game process"))) return;
            Seed(); if (!Check(Runtime->TryActivate(AbilityId,Pawn,Error),TEXT("Restored ability can cast: ")+Error)) return;
            Step=20; Next=Now+2.3; return;
        }
        auto W=Clone(Store->Document().Get()),A=Clone(Find(W,TEXT("abilities"),TEXT("battle_prelate.martyr_s_ward")));
        if (!Check(A.IsValid(),TEXT("Approved presentation baseline exists"))) return;
        A->SetStringField(TEXT("id"),AbilityId.ToString()); A->SetStringField(TEXT("name"),TEXT("Personal workshop heal")); A->SetBoolField(TEXT("legacyTargeting"),false);
        A->SetObjectField(TEXT("targeting"),Parse(TEXT(R"({"target":"self","shape":"self","range":0,"maxTargets":1})")));
        A->SetObjectField(TEXT("timing"),Parse(TEXT(R"({"mode":"cast","castSec":2})"))); A->SetObjectField(TEXT("resource"),Parse(TEXT(R"({"manaCost":10,"careerBuild":0,"careerCost":0})"))); A->SetNumberField(TEXT("cooldownSec"),20);
        const auto Parts=Parse(TEXT(R"({"effects":[{"id":"heal","kind":"heal","recipient":"caster","amount":{"min":20,"max":20}}],"conditions":[{"id":"no_hot","event":"application","condition":{"kind":"all","children":[{"kind":"hot","subject":"recipient","source":"self","not":true}]},"actions":[{"kind":"percent","effectId":"heal","value":0.5}]}]})"));
        A->SetArrayField(TEXT("effects"),Array(Parts,TEXT("effects"))); A->SetArrayField(TEXT("conditions"),Array(Parts,TEXT("conditions")));
        auto Abilities=Array(W,TEXT("abilities")); Abilities.Add(MakeShared<FJsonValueObject>(A)); W->SetArrayField(TEXT("abilities"),Abilities);
        auto Assignment=Parse(TEXT(R"({"id":"personal.proof_assignment","classId":"battle_prelate","abilityId":"workshop.personal_heal","unlockLevel":1,"displayOrder":11,"overrides":[],"presentations":{"civic_battle_prelate_m":"battle_prelate.martyr_s_ward"}})"));
        auto Assignments=Array(W,TEXT("assignments")); Assignments.Add(MakeShared<FJsonValueObject>(Assignment)); W->SetArrayField(TEXT("assignments"),Assignments);
        if (!Check(Store->Document().Commit(W,Error),TEXT("Structured draft commits: ")+Error)) return;
        if (!Check(Store->ApplyToDevelopment(PC),TEXT("Personal deploy API accepts authorized draft: ")+Store->GetMessage())) return;
        if (!Check(!Catalog->Find(AbilityId,Pawn->GetCareerId()),TEXT("Staging does not mutate the catalog mid-tick"))) return;
        Step=1; Next=Now+.2; return;
    }
    if (Step==1) {
        FirstVersion=Catalog->GetVersion().RightChop(9);
        if (!Check(Catalog->Kit(Pawn->GetCareerId()).Num()==11 && Store->PersonalHistory().Num()==1,TEXT("Deployment activates and records the eleventh class ability"))) return;
        Seed(); if (!Check(Runtime->TryActivate(AbilityId,Pawn,Error),TEXT("Deployed ability starts a real cast: ")+Error)) return;
        auto W=Clone(Store->Document().Get()); auto Amount=Object(Find(Find(W,TEXT("abilities"),AbilityId.ToString()),TEXT("effects"),TEXT("heal")),TEXT("amount")); Amount->SetNumberField(TEXT("min"),40); Amount->SetNumberField(TEXT("max"),40);
        if (!Check(Store->Document().Commit(W,Error) && Store->ApplyToDevelopment(PC),TEXT("Second deployment stages during the first cast: ")+Store->GetMessage())) return;
        Step=2; Next=Now+2.3; return;
    }
    if (Step==2) {
        if (!Check(State->GetAttributes()->GetHealth()==40,TEXT("In-flight cast retains old conditional amount (20 x 1.5)"))) return;
        if (!Check(Runtime->Cooldown(AbilityId)>15 && State->GetAttributes()->GetMana()==90,TEXT("Deployment preserves cooldown and spent mana"))) return;
        Seed(); if (!Check(Runtime->TryActivate(AbilityId,Pawn,Error),TEXT("New cast uses deployed version: ")+Error)) return;
        Step=3; Next=Now+2.3; return;
    }
    if (Step==3) {
        if (!Check(State->GetAttributes()->GetHealth()==70,TEXT("New cast uses updated conditional amount (40 x 1.5)"))) return;
        if (!Check(Store->RollbackPersonal(PC,FirstVersion),TEXT("Rollback queues an immutable prior version: ")+Store->GetMessage())) return;
        Step=4; Next=Now+.2; return;
    }
    if (Step==4) {
        if (!Check(Catalog->GetVersion()==TEXT("personal-")+FirstVersion && Runtime->Cooldown(AbilityId)>15,TEXT("Rollback activates while preserving existing cooldown"))) return;
        Seed(); if (!Check(Runtime->TryActivate(AbilityId,Pawn,Error),TEXT("Rolled-back ability casts: ")+Error)) return;
        Step=5; Next=Now+2.3; return;
    }
    if (Step==5 || Step==20) {
        if (!Check(State->GetAttributes()->GetHealth()==40,TEXT("Confirmed saved version produces its original conditional heal"))) return;
        if (Step==20) { Finish(true,TEXT("Durable restart restoration verified")); return; }
        if (!Check(Store->RestoreShipped(PC),TEXT("Restore-shipped uses the ordinary deployment API"))) return;
        Step=6; Next=Now+.2; return;
    }
    if (Step==6) {
        if (!Check(!Catalog->Find(AbilityId,Pawn->GetCareerId()) && Catalog->Kit(Pawn->GetCareerId()).Num()==10,TEXT("Restoring shipped definitions removes the custom assignment"))) return;
        if (!Check(!Runtime->TryActivate(AbilityId,Pawn,Error),TEXT("Removed assignment blocks future activations"))) return;
        if (!Check(Store->RollbackPersonal(PC,FirstVersion),TEXT("Saved custom version can be restored after assignment removal"))) return;
        Step=7; Next=Now+.2; return;
    }
    if (Step==7) {
        if (!Check(Catalog->GetVersion()==TEXT("personal-")+FirstVersion,TEXT("Final confirmed version is saved for the restart check"))) return;
        Finish(true,TEXT("Personal deployment, real casts, rollback and restore-shipped verified"));
    }
}
