#include "WarAbilityWorkshopCombatProof.h"
#include "WarAbilityWorkshopDocument.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityRuntime.h"
#include "WarCombatStatus.h"
#include "WarContentSubsystem.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"

using namespace WarWorkshopJson;
namespace
{
    const FName TestId(TEXT("workshop.proof_heal"));
    FString Folder()
    {
        FString Run; FGuid Id;
        if (!FParse::Value(FCommandLine::Get(),TEXT("WarWorkshopRun="),Run) || !FGuid::Parse(Run,Id)) return TEXT("");
        return FPaths::ProjectSavedDir()/TEXT("AbilityWorkshopCombatProof")/Id.ToString(EGuidFormats::Digits);
    }
}
bool UWarAbilityWorkshopCombatProof::ShouldCreateSubsystem(UObject* Outer) const
{ return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarWorkshopCombatProof")) && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking")) && !Folder().IsEmpty(); }
TStatId UWarAbilityWorkshopCombatProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarAbilityWorkshopCombatProof,STATGROUP_Tickables); }
bool UWarAbilityWorkshopCombatProof::Check(bool Passed,const FString& Label)
{ if (!Passed) { Finish(false,Label); return false; } Checks.Add(Label); return true; }
void UWarAbilityWorkshopCombatProof::Finish(bool Passed,const FString& Error)
{
    bFinished=true; auto Report=MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"),Passed); Report->SetStringField(TEXT("detail"),Error);
    Report->SetBoolField(TEXT("sharedAdmission"),false); Report->SetBoolField(TEXT("onlineExecutor"),GetWorld()->GetNetMode()!=NM_Standalone);
    TArray<TSharedPtr<FJsonValue>> Values; for (const auto& C:Checks) Values.Add(MakeShared<FJsonValueString>(C)); Report->SetArrayField(TEXT("checks"),Values);
    IFileManager::Get().MakeDirectory(*Folder(),true);
    FFileHelper::SaveStringToFile(WarWorkshopJson::Serialize(Report),*(Folder()/(GetWorld()->GetNetMode()==NM_Client ? TEXT("client.json") : TEXT("server.json"))));
    UE_LOG(LogTemp,Display,TEXT("WAR_WORKSHOP_COMBAT %s %s"),Passed ? TEXT("passed") : TEXT("FAILED"),*Error);
    // The harness owns process lifetime so the server remains available for final client synchronization.
}
bool UWarAbilityWorkshopCombatProof::Stage(int32 Version,float Heal,float Tick,float Percent)
{
    auto A=Find(Workspace,TEXT("abilities"),TestId.ToString());
    auto Amount=Object(Find(A,TEXT("effects"),TEXT("heal")),TEXT("amount")); Amount->SetNumberField(TEXT("min"),Heal); Amount->SetNumberField(TEXT("max"),Heal);
    Amount=Object(Find(A,TEXT("effects"),TEXT("hot")),TEXT("amount")); Amount->SetNumberField(TEXT("min"),Tick); Amount->SetNumberField(TEXT("max"),Tick);
    Array(Find(A,TEXT("conditions"),TEXT("application_bonus")),TEXT("actions"))[0]->AsObject()->SetNumberField(TEXT("value"),Percent);
    FString Error; return Check(GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>()->StageWorkspace(WarWorkshopJson::Serialize(Workspace),FString::Printf(TEXT("workshop-proof-%d"),Version),Error),TEXT("Stage complete version: ")+Error);
}
void UWarAbilityWorkshopCombatProof::Tick(float Delta)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds(); if (Now<Next) return;
    if (Now>150) { Finish(false,TEXT("Timed out waiting for authoritative workshop proof")); return; }
    auto* Catalog=GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()); auto* Pawn=PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* State=PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!Pawn || !State || !Pawn->IsVisualReady() || Pawn->GetCharacterMovement()->IsFalling()) return;
    if (GetWorld()->GetNetMode()==NM_Client)
    {
        if (Catalog->GetVersion()!=TEXT("workshop-proof-4")) return;
        const auto* A=Catalog->Find(TestId,Pawn->GetCareerId());
        if (!Check(A && A->Effects[0].Minimum==10,TEXT("Client receives complete rolled-back catalog"))) return;
        if (!Check(!PC->CanUseGmTools(),TEXT("Network fixture grants no client GM privilege"))) return;
        Finish(true,TEXT("Version synchronization after authoritative changes")); return;
    }
    auto* Runtime=State->GetClassAbilities(); auto* Status=UWarCombatStatus::On(Pawn); auto* ASC=State->GetAbilitySystemComponent(); FString Error;
    const auto Health=[&] { return State->GetAttributes()->GetHealth(); };
    const auto Seed=[&] {
        Runtime->Interrupt(); Status->Clear(); ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),20); Runtime->ResetCooldowns(); Runtime->RestoreResource();
        FWarAbilityDefinition Definition; Definition.Id=TEXT("proof.seed"); Definition.Range=100; Definition.Version=TEXT("seed");
        FWarAbilityEffect Hot; Hot.Id=TEXT("seed_hot"); Hot.Kind=TEXT("heal"); Hot.Recipient=TEXT("caster"); Hot.PeriodicDuration=30; Hot.Interval=10;
        Status->ApplyPeriodic(Hot,0,Pawn,Pawn,MakeShared<const FWarAbilityDefinition>(Definition),10,1,true);
    };
    if (Step==0)
    {
        FWarAbilityWorkshopDocument Document; if (!Check(Document.Baseline(GetWorld()->GetGameInstance()->GetSubsystem<UWarContentSubsystem>()->GetInterfaceCatalogSource(),Error),Error)) return;
        Workspace=Clone(Document.Get()); auto Ability=Clone(Find(Workspace,TEXT("abilities"),TEXT("battle_prelate.martyr_s_ward")));
        if (!Check(Ability.IsValid(),TEXT("Approved Prelate baseline exists"))) return;
        Ability->SetStringField(TEXT("id"),TestId.ToString()); Ability->SetStringField(TEXT("name"),TEXT("Workshop conditional proof")); Ability->SetBoolField(TEXT("legacyTargeting"),false);
        Ability->SetObjectField(TEXT("targeting"),Parse(TEXT(R"({"target":"self","shape":"self","range":0,"maxTargets":1})")));
        Ability->SetObjectField(TEXT("timing"),Parse(TEXT(R"({"mode":"cast","castSec":2})"))); Ability->SetObjectField(TEXT("resource"),Parse(TEXT(R"({"manaCost":10,"careerBuild":0,"careerCost":0})"))); Ability->SetNumberField(TEXT("cooldownSec"),20);
        const auto Components=Parse(TEXT(R"({"effects":[{"id":"heal","kind":"heal","recipient":"caster","amount":{"min":10,"max":10}},{"id":"hot","kind":"heal","recipient":"caster","amount":{"min":2,"max":2},"periodic":{"durationSec":8,"intervalSec":1}}],"conditions":[{"id":"start_bonus","name":"Cast snapshot","event":"cast_start","condition":{"kind":"all","children":[{"kind":"hot","subject":"caster","source":"self"}]},"actions":[{"kind":"flat","effectId":"heal","value":5}]},{"id":"application_bonus","name":"Application snapshot","event":"application","condition":{"kind":"all","children":[{"kind":"hot","subject":"recipient","source":"self"}]},"actions":[{"kind":"percent","effectId":"heal","value":0.25}]},{"id":"tick_bonus","name":"Fresh tick snapshot","event":"tick","condition":{"kind":"all","children":[{"kind":"hot","subject":"recipient","source":"self"}]},"actions":[{"kind":"percent","effectId":"hot","value":0.5}]}]})"));
        Ability->SetArrayField(TEXT("effects"),Array(Components,TEXT("effects"))); Ability->SetArrayField(TEXT("conditions"),Array(Components,TEXT("conditions")));
        auto Abilities=Array(Workspace,TEXT("abilities")); Abilities.Add(MakeShared<FJsonValueObject>(Ability)); Workspace->SetArrayField(TEXT("abilities"),Abilities);
        auto Assignment=Parse(TEXT(R"({"id":"proof.assignment","classId":"battle_prelate","abilityId":"workshop.proof_heal","unlockLevel":1,"displayOrder":11,"overrides":[],"presentations":{"civic_battle_prelate_m":"battle_prelate.martyr_s_ward"}})"));
        auto Assignments=Array(Workspace,TEXT("assignments")); Assignments.Add(MakeShared<FJsonValueObject>(Assignment)); Workspace->SetArrayField(TEXT("assignments"),Assignments);
        ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),600); ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),10); Runtime->RestoreResource(); Status->Clear();
        if (!Stage(1,10,2,.25)) return; Step=1; Next=Now+.2; return;
    }
    if (Step==1)
    {
        if (!Check(Catalog->Kit(Pawn->GetCareerId()).Num()==11,TEXT("Native class supports more than ten assignments"))) return;
        if (!Check(Runtime->TryActivate(TestId,Pawn,Error),TEXT("First activation: ")+Error)) return;
        if (!Check(Runtime->GetActionState()==TEXT("casting"),TEXT("Windup is an explicit casting state"))) return;
        Step=2; Next=Now+.35; return;
    }
    if (Step==2) { if (!Stage(2,30,4,.5)) return; Step=3; Next=Now+1.8; return; }
    if (Step==3)
    {
        if (!Check(Health()==20,TEXT("Old activation retains definition; its own newly applied HoT cannot qualify the same impact"))) return;
        if (!Check(Runtime->Cooldown(TestId)>15 && State->GetAttributes()->GetMana()==90,TEXT("Publication preserves cooldown deadline and spent mana"))) return;
        if (!Check(Status->GetActive().ContainsByPredicate([](const auto& S) { return S.AppliedVersion==TEXT("workshop-proof-1"); }),TEXT("Periodic status retains original applied version"))) return;
        Step=4; Next=Now+1; return;
    }
    if (Step==4)
    {
        if (!Check(Health()==23,TEXT("Old periodic baseline survives publication; tick observes the earlier HoT and adds 50% once"))) return;
        Seed(); if (!Check(Runtime->TryActivate(TestId,Pawn,Error),TEXT("Second activation: ")+Error)) return;
        Step=5; Next=Now+.3; return;
    }
    if (Step==5) { Status->Clear(); if (!Stage(3,100,20,.5)) return; Step=6; Next=Now+1.85; return; }
    if (Step==6)
    {
        if (!Check(Health()==55,TEXT("Cast-start flat bonus survives removed HoT; application bonus fails after removal; in-flight definition remains v2"))) return;
        Step=7; Next=Now+1; return;
    }
    if (Step==7)
    {
        if (!Check(Health()==61,TEXT("Application-adjusted v2 periodic baseline is reevaluated without accumulation"))) return;
        Seed(); if (!Check(Runtime->TryActivate(TestId,Pawn,Error),TEXT("Third activation: ")+Error)) return;
        Step=8; Next=Now+2.2; return;
    }
    if (Step==8)
    {
        if (!Check(Health()==178,TEXT("New cast uses v3 and combines (100 + 5) × 1.5, then rounds"))) return;
        if (!Stage(4,10,2,.25)) return; Step=9; Next=Now+1; return;
    }
    if (Step==9)
    {
        if (!Check(Health()==208,TEXT("Rollback affects future casts only; v3 periodic status still ticks for 30"))) return;
        if (!Check(Catalog->GetVersion()==TEXT("workshop-proof-4") && Runtime->Cooldown(TestId)>15,TEXT("Rollback preserves existing cooldown"))) return;
        auto Report=MakeShared<FJsonObject>(); TArray<TSharedPtr<FJsonValue>> Traces;
        for (const auto& T:Runtime->GetConditionTraces()) { auto J=MakeShared<FJsonObject>(); J->SetStringField(TEXT("rule"),T.RuleId.ToString()); J->SetStringField(TEXT("event"),T.Event.ToString()); J->SetStringField(TEXT("recipient"),T.RecipientId.ToString()); J->SetNumberField(TEXT("time"),T.At); J->SetBoolField(TEXT("passed"),T.bPassed); Traces.Add(MakeShared<FJsonValueObject>(J)); }
        Report->SetArrayField(TEXT("traces"),Traces); IFileManager::Get().MakeDirectory(*Folder(),true); FFileHelper::SaveStringToFile(WarWorkshopJson::Serialize(Report),*(Folder()/TEXT("traces.json")));
        Finish(true,TEXT("Authoritative conditional execution, immutable casts/statuses and rollback verified"));
    }
}
