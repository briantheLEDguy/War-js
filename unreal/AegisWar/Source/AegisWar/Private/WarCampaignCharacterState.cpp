#include "WarPlayerState.h"
#include "WarAbilityRuntime.h"
#include "WarCombatStatus.h"
#include "WarCampaignCombatState.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "WarCharacter.h"

TSharedPtr<FJsonObject> UWarAbilityRuntime::CaptureCampaignState(int64 CapturedAt) const
{
    const double Time=Now(); auto State=MakeShared<FJsonObject>(); State->SetNumberField(TEXT("resource"),Resource);
    if (GcdUntil>Time && GcdExpiresAtUnixMs<=0) return nullptr;
    const double GcdRemaining=FMath::Max(0.,(GcdExpiresAtUnixMs-CapturedAt)/1000.); State->SetNumberField(TEXT("globalCooldown"),GcdRemaining);
    State->SetNumberField(TEXT("globalCooldownExpiresAtUnixMs"),GcdExpiresAtUnixMs);
    TArray<TSharedPtr<FJsonValue>> Entries;
    for (const auto& Cooldown:Cooldowns) if (Cooldown.Until>Time)
    {
        if (Cooldown.ExpiresAtUnixMs<=0) return nullptr;
        auto Entry=MakeShared<FJsonObject>(); Entry->SetStringField(TEXT("id"),Cooldown.Id.ToString());
        Entry->SetNumberField(TEXT("remaining"),FMath::Max(0.,(Cooldown.ExpiresAtUnixMs-CapturedAt)/1000.));Entry->SetNumberField(TEXT("expiresAtUnixMs"),Cooldown.ExpiresAtUnixMs);
        Entries.Add(MakeShared<FJsonValueObject>(Entry));
    }
    State->SetArrayField(TEXT("cooldowns"),Entries); return State;
}
bool UWarAbilityRuntime::RestoreCampaignState(const TSharedPtr<FJsonObject>& State,int64 CapturedAt,int64 CurrentUtc,FString& Error,bool Apply)
{
    using namespace WarCampaignCombatState;
    double SavedResource=0,GcdRemaining=0,GcdExpiry=0; const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
    const auto Deadline=[&](double Remaining,double Expiry,double Limit) { return Remaining<=Limit && FMath::Abs(FMath::Max(0.,(Expiry-CapturedAt)/1000.)-Remaining)<=.01; };
    if (!State || State->Values.Num()!=4 || !Number(State,TEXT("resource"),SavedResource) || !Number(State,TEXT("globalCooldown"),GcdRemaining,0,60)
        || !Epoch(State,TEXT("globalCooldownExpiresAtUnixMs"),GcdExpiry) || !Deadline(GcdRemaining,GcdExpiry,60)
        || !State->TryGetArrayField(TEXT("cooldowns"),Entries) || Entries->Num()>256)
    { Error=TEXT("Invalid campaign ability epoch snapshot."); return false; }
    TArray<FWarAbilityCooldown> Restored; TSet<FString> Ids; const double Time=Now();
    for (const auto& Value:*Entries)
    {
        const auto Row=Value.IsValid() && Value->Type==EJson::Object ? Value->AsObject() : nullptr; FString Id; double Remaining=0,Expiry=0;
        if (!Row || Row->Values.Num()!=3 || !Row->HasTypedField<EJson::String>(TEXT("id")) || !Row->TryGetStringField(TEXT("id"),Id) || Id.IsEmpty() || Id.Len()>160 || Ids.Contains(Id)
            || !Number(Row,TEXT("remaining"),Remaining,0,3600) || !Epoch(Row,TEXT("expiresAtUnixMs"),Expiry) || !Deadline(Remaining,Expiry,3600))
        { Error=TEXT("Invalid campaign cooldown identity or deadline."); return false; }
        Ids.Add(Id);
        if (Expiry>CurrentUtc) { FWarAbilityCooldown Cooldown; Cooldown.Id=FName(*Id); Cooldown.Until=Time+(Expiry-CurrentUtc)/1000.;Cooldown.ExpiresAtUnixMs=int64(Expiry); Restored.Add(Cooldown); }
    }
    const auto Kit=Catalog() ? Catalog()->Kit(Career) : TArray<const FWarAbilityDefinition*>();
    if (!Kit.IsEmpty() && SavedResource>Kit[0]->ResourceMax) { Error=TEXT("Saved ability resource exceeds its native character definition."); return false; }
    if (Apply)
    {
        Resource=SavedResource; GcdUntil=Time+FMath::Max(0.,(GcdExpiry-CurrentUtc)/1000.);GcdExpiresAtUnixMs=int64(GcdExpiry); Cooldowns=MoveTemp(Restored); GetOwner()->ForceNetUpdate();
    }
    return true;
}
TSharedPtr<FJsonObject> AWarPlayerState::CaptureCampaignState(FString& Error) const
{
    using namespace WarCampaignCombatState;
    const int64 CapturedAt=UnixMs(); auto State=CaptureScenarioState(); State->SetNumberField(TEXT("version"),2); State->SetNumberField(TEXT("capturedAtUnixMs"),CapturedAt);
    const auto Abilities=ClassAbilities->CaptureCampaignState(CapturedAt);
    if (!Abilities) { Error=TEXT("An active cooldown lacks its original fixed custody deadline.");return nullptr; }
    State->SetObjectField(TEXT("abilities"),Abilities); State->SetBoolField(TEXT("dead"),Attributes->GetHealth()<=0);
    auto* Status=UWarCombatStatus::On(GetPawn()); TSharedPtr<FJsonObject> Combat;
    if (Status && Attributes->GetHealth()>0) { if (!Status->CaptureCampaignState(CapturedAt,Combat,Error)) return nullptr; }
    else { Combat=MakeShared<FJsonObject>(); Combat->SetNumberField(TEXT("version"),1); Combat->SetArrayField(TEXT("definitions"),{}); Combat->SetArrayField(TEXT("statuses"),{}); }
    TArray<TSharedPtr<FJsonValue>> Effects;
    if (!CaptureAsc(AbilitySystem,CapturedAt,Effects,Error)) return nullptr;
    Combat->SetArrayField(TEXT("ascEffects"),Effects); State->SetObjectField(TEXT("combat"),Combat);
    if (!ClassAbilities->RestoreCampaignState(State->GetObjectField(TEXT("abilities")),CapturedAt,CapturedAt,Error,false)) return nullptr;
    return State;
}
bool AWarPlayerState::RestoreCampaignState(const TSharedPtr<FJsonObject>& State,FString& Error,bool Respawn,int64 CurrentUtc)
{
    using namespace WarCampaignCombatState;
    if (!State || !HasAuthority()) { Error=TEXT("Character custody is unavailable."); return false; }
    double Version=0;
    if (!State->HasField(TEXT("version")) || (State->HasTypedField<EJson::Number>(TEXT("version")) && State->TryGetNumberField(TEXT("version"),Version) && Version==1))
    {
        if (State->HasField(TEXT("combat")) || State->HasField(TEXT("capturedAtUnixMs"))) { Error=TEXT("Partial campaign runtime cannot use historical recovery rules."); return false; }
        const TSharedPtr<FJsonObject>* LegacyAbilities=nullptr;
        if (State->TryGetObjectField(TEXT("abilities"),LegacyAbilities))
        {
            const TArray<TSharedPtr<FJsonValue>>* LegacyCooldowns=nullptr;
            if ((*LegacyAbilities)->HasField(TEXT("globalCooldownExpiresAtUnixMs"))) { Error=TEXT("Partial campaign cooldown epochs cannot use historical timers."); return false; }
            if ((*LegacyAbilities)->TryGetArrayField(TEXT("cooldowns"),LegacyCooldowns)) for (const auto& Value:*LegacyCooldowns)
                if (Value && Value->Type==EJson::Object && Value->AsObject()->HasField(TEXT("expiresAtUnixMs")))
                { Error=TEXT("Partial campaign cooldown epochs cannot use historical timers."); return false; }
        }
        RestoreScenarioState(State); return true;
    }
    double CapturedAt=0,Health=0,Mana=0; bool Dead=false;
    const TSharedPtr<FJsonObject>* Abilities=nullptr; const TSharedPtr<FJsonObject>* Combat=nullptr; const TArray<TSharedPtr<FJsonValue>>* Effects=nullptr; const TArray<TSharedPtr<FJsonValue>>* StatusRows=nullptr;
    if (Version!=2 || State->Values.Num()!=9 || !Epoch(State,TEXT("capturedAtUnixMs"),CapturedAt) || CapturedAt<=0
        || !Number(State,TEXT("health"),Health,0,MAX_flt) || !Number(State,TEXT("mana"),Mana,0,MAX_flt) || !State->HasTypedField<EJson::Boolean>(TEXT("dead")) || !State->TryGetBoolField(TEXT("dead"),Dead)
        || !State->TryGetObjectField(TEXT("abilities"),Abilities) || !State->TryGetObjectField(TEXT("combat"),Combat) || (*Combat)->Values.Num()!=4
        || !(*Combat)->TryGetArrayField(TEXT("ascEffects"),Effects) || !(*Combat)->TryGetArrayField(TEXT("statuses"),StatusRows))
    { Error=TEXT("Invalid complete campaign runtime v2."); return false; }
    TSet<FGuid> Rewards,Kills;
    const auto ReadReceipts=[&](const TCHAR* Field,TSet<FGuid>& Receipts) {
        const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
        if (!State->TryGetArrayField(Field,Rows) || Rows->Num()>65536) return false;
        for (const auto& Value:*Rows) { FGuid Id; if (!Value || Value->Type!=EJson::String || !FGuid::Parse(Value->AsString(),Id) || Receipts.Contains(Id)) return false; Receipts.Add(Id); }
        return true;
    };
    if (!ReadReceipts(TEXT("rewards"),Rewards) || !ReadReceipts(TEXT("questKills"),Kills)) { Error=TEXT("Invalid durable character receipts."); return false; }
    if (CurrentUtc==0) CurrentUtc=UnixMs();
    auto* Status=UWarCombatStatus::On(GetPawn()); const bool ClearPawn=Respawn || Dead;
    if (!Status && !StatusRows->IsEmpty() && !ClearPawn)
    { Error=TEXT("Saved pawn effects await the authentic character avatar."); return false; }
    auto* Validator=Status ? Status : NewObject<UWarCombatStatus>(this);
    if (!ClassAbilities->RestoreCampaignState(*Abilities,CapturedAt,CurrentUtc,Error,false)
        || !RestoreAsc(AbilitySystem,*Effects,CurrentUtc,Error,false)
        || !Validator->RestoreCampaignState(*Combat,CurrentUtc,Error,false,ClearPawn)) return false;
    if (!RestoreAsc(AbilitySystem,*Effects,CurrentUtc,Error,true)) return false;
    if (Status && !Status->RestoreCampaignState(*Combat,CurrentUtc,Error,true,ClearPawn)) return false;
    ClassAbilities->RestoreCampaignState(*Abilities,CapturedAt,CurrentUtc,Error,true);
    AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),Respawn ? Attributes->GetMaxHealth() : FMath::Clamp(float(Health),0.f,Attributes->GetMaxHealth()));
    AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),Respawn ? Attributes->GetMaxMana() : FMath::Clamp(float(Mana),0.f,Attributes->GetMaxMana()));
    RewardReceipts=MoveTemp(Rewards); QuestKillReceipts=MoveTemp(Kills); ForceNetUpdate(); return true;
}
