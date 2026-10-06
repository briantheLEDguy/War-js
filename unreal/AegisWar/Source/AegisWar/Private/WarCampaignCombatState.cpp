#include "WarCampaignCombatState.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarSiegeGameMode.h"
#include "WarGameplayEffects.h"
#include "AbilitySystemComponent.h"
#include "EngineUtils.h"
#include "Engine/Level.h"
#include "UObject/Package.h"
#include "Internationalization/Regex.h"
#include "Misc/DateTime.h"

void AWarPlayerState::CampaignEffectAdded(UAbilitySystemComponent* Component,const FGameplayEffectSpec& Spec,FActiveGameplayEffectHandle Handle)
{
    if (!HasAuthority() || Component!=AbilitySystem || !Spec.Def || Spec.Def->GetClass()!=UWarStrikeCooldownEffect::StaticClass()) return;
    const auto* Active=AbilitySystem->GetActiveGameplayEffect(Handle);const float Duration=Spec.GetDuration();
    if (!Active || !FMath::IsFinite(Duration) || Duration<=0 || Duration>3600) return;
    CampaignEffectEpochs.Add(Handle,{WarCampaignCombatState::UnixMs()+FMath::RoundToInt64(Duration*1000.),Active->GetEndTime(),Duration});
}
void AWarPlayerState::CampaignEffectRemoved(const FActiveGameplayEffect& Effect)
{ CampaignEffectEpochs.Remove(Effect.Handle); }
bool AWarPlayerState::GetCampaignEffectEpoch(FActiveGameplayEffectHandle Handle,int64& Expiry) const
{
    const auto* Recorded=CampaignEffectEpochs.Find(Handle);const auto* Active=AbilitySystem->GetActiveGameplayEffect(Handle);
    if (!HasAuthority() || !Recorded || !Active || !Active->Spec.Def || Active->Spec.Def->GetClass()!=UWarStrikeCooldownEffect::StaticClass()
        || Recorded->Expiry<=0 || Recorded->Duration!=Active->GetDuration() || Recorded->WorldEnd!=Active->GetEndTime()) return false;
    Expiry=Recorded->Expiry;return true;
}
bool AWarPlayerState::RestoreCampaignEffectEpoch(FActiveGameplayEffectHandle Handle,int64 Expiry)
{
    const auto* Active=AbilitySystem->GetActiveGameplayEffect(Handle);
    if (!HasAuthority() || !Active || !Active->Spec.Def || Active->Spec.Def->GetClass()!=UWarStrikeCooldownEffect::StaticClass()
        || Expiry<=0 || Expiry>9007199254740991LL) return false;
    CampaignEffectEpochs.Add(Handle,{Expiry,Active->GetEndTime(),Active->GetDuration()});return true;
}

namespace WarCampaignCombatState
{
    int64 UnixMs() { return (FDateTime::UtcNow().GetTicks() - FDateTime(1970,1,1).GetTicks()) / ETimespan::TicksPerMillisecond; }
    bool ValidKey(const FString& Key, bool AllowEmpty)
    {
        if (Key.IsEmpty()) return AllowEmpty;
        if (Key.Len()>512 || Key.Contains(TEXT("..")) || Key.Contains(TEXT("//"))) return false;
        static const FRegexPattern HumanPattern(TEXT("^human:([a-zA-Z0-9_-]{1,80})$"));
        static const FRegexPattern AuthoredPattern(TEXT("^authored:/Game/[a-zA-Z0-9_/-]+#War(?:World|Zone)Object_[a-zA-Z0-9_]+$"));
        static const FRegexPattern EncounterPattern(TEXT("^encounter:[a-zA-Z0-9_:-]{1,160}:[012]:(?:aegis|riftbound):[a-zA-Z0-9_-]{1,80}:([0-9]{1,3}):(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$"));
        FRegexMatcher Human(HumanPattern,Key);
        if (Human.FindNext()) return Human.GetCaptureGroup(1)!=TEXT("constructor") && Human.GetCaptureGroup(1)!=TEXT("prototype") && Human.GetCaptureGroup(1)!=TEXT("__proto__");
        FRegexMatcher Authored(AuthoredPattern,Key);
        if (Authored.FindNext()) return true;
        FRegexMatcher Encounter(EncounterPattern,Key);
        return Encounter.FindNext() && FCString::Atoi(*Encounter.GetCaptureGroup(1))<=127;
    }
    bool KeyFor(const AActor* Actor, FString& Key, FString& Error)
    {
        Key.Reset();
        if (!IsValid(Actor)) { Error=TEXT("An applied effect has no authenticated source identity."); return false; }
        const auto* Pawn=Cast<APawn>(Actor);
        const auto* Controller=Pawn ? Pawn->GetController() : Cast<AController>(Actor);
        if (const auto* Human=Cast<AWarPlayerController>(Controller))
        { if (Human->bCampaignIdentityProvisioned) Key=TEXT("human:")+Human->ScenarioCharacterId; }
        else if (const auto* Bot=Cast<AWarSiegeBotController>(Controller)) Key=Bot->CampaignCombatSourceKey;
        else if (Actor->GetLevel())
        {
            TArray<FName> IdentityTags;
            for (FName Tag:Actor->Tags) if (Tag.ToString().StartsWith(TEXT("WarWorldObject_")) || Tag.ToString().StartsWith(TEXT("WarZoneObject_"))) IdentityTags.Add(Tag);
            if (IdentityTags.Num()==1) Key=TEXT("authored:")+Actor->GetLevel()->GetOutermost()->GetName()+TEXT("#")+IdentityTags[0].ToString();
        }
        if (!ValidKey(Key)) { Key.Reset(); Error=TEXT("An applied effect source or target is not durably provisioned. Recovery remains protected until expiry."); return false; }
        return true;
    }
    AActor* Resolve(UWorld* World, const FString& Key)
    {
        if (!World || !ValidKey(Key)) return nullptr;
        AActor* Match=nullptr;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (It->IsA<AController>()) continue;
            FString Candidate,Ignored;
            if (KeyFor(*It,Candidate,Ignored) && Candidate==Key)
            { if (Match) return nullptr; Match=*It; }
        }
        return Match;
    }
    bool Number(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, double& Value, double Minimum, double Maximum)
    { return Object && Object->HasTypedField<EJson::Number>(Field) && Object->TryGetNumberField(Field,Value) && FMath::IsFinite(Value) && Value>=Minimum && Value<=Maximum; }
    bool Epoch(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, double& Value)
    { return Number(Object,Field,Value,0,9007199254740991.) && FMath::FloorToDouble(Value)==Value; }
    bool CaptureAsc(UAbilitySystemComponent* Asc, int64 CapturedAt, TArray<TSharedPtr<FJsonValue>>& Rows, FString& Error)
    {
        Rows.Reset(); if (!Asc) { Error=TEXT("Character ability system is not ready for custody."); return false; }
        for (const auto& Handle:Asc->GetActiveEffects(FGameplayEffectQuery()))
        {
            const auto* Effect=Asc->GetActiveGameplayEffect(Handle);
            if (!Effect || !Effect->Spec.Def || Effect->Spec.Def->GetClass()!=UWarStrikeCooldownEffect::StaticClass() || Effect->Spec.GetStackCount()!=1 || !Rows.IsEmpty())
            { Error=TEXT("An opaque native gameplay effect cannot be safely persisted. Character custody remains protected."); return false; }
            const double Remaining=Effect->GetTimeRemaining(Asc->GetWorld()->GetTimeSeconds());
            if (!FMath::IsFinite(Remaining) || Remaining>3600 || !FMath::IsFinite(Effect->Spec.GetLevel()) || Effect->Spec.GetLevel()<=0 || Effect->Spec.GetLevel()>1000)
            { Error=TEXT("Unsupported native cooldown duration or level."); return false; }
            if (Remaining<=0) continue;
            const auto* Owner=Cast<AWarPlayerState>(Asc->GetOwner());int64 Expiry=0;
            if (!Owner || !Owner->GetCampaignEffectEpoch(Handle,Expiry))
            { Error=TEXT("A supported native cooldown lacks its actual application deadline or changed without an application event.");return false; }
            auto Row=MakeShared<FJsonObject>(); Row->SetStringField(TEXT("id"),TEXT("DevelopmentStrikeCooldown"));
            Row->SetNumberField(TEXT("expiresAtUnixMs"),Expiry);
            Row->SetNumberField(TEXT("level"),Effect->Spec.GetLevel()); Row->SetNumberField(TEXT("stacks"),1);
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        return true;
    }
    bool RestoreAsc(UAbilitySystemComponent* Asc, const TArray<TSharedPtr<FJsonValue>>& Rows, int64 CurrentUtc, FString& Error, bool Apply)
    {
        TArray<TSharedPtr<FJsonValue>> Existing;
        if (!CaptureAsc(Asc,CurrentUtc,Existing,Error) || Rows.Num()>1) return false;
        FGameplayEffectSpecHandle Spec;int64 SavedExpiry=0;
        for (const auto& Value:Rows)
        {
            const auto Row=Value.IsValid() && Value->Type==EJson::Object ? Value->AsObject() : nullptr;
            FString Id; double Expiry=0,Level=0,Stacks=0;
            if (!Row || Row->Values.Num()!=4 || !Row->HasTypedField<EJson::String>(TEXT("id")) || !Row->TryGetStringField(TEXT("id"),Id) || Id!=TEXT("DevelopmentStrikeCooldown")
                || !Epoch(Row,TEXT("expiresAtUnixMs"),Expiry) || !Number(Row,TEXT("level"),Level,.00001,1000) || !Number(Row,TEXT("stacks"),Stacks,1,1))
            { Error=TEXT("Invalid supported native cooldown snapshot."); return false; }
            const float Remaining=FMath::Max(0.,(Expiry-CurrentUtc)/1000.);
            if (Remaining>3600) { Error=TEXT("Native cooldown exceeds the recorded duration bound."); return false; }
            if (Remaining>0)
            {
                Spec=Asc->MakeOutgoingSpec(UWarStrikeCooldownEffect::StaticClass(),Level,Asc->MakeEffectContext());
                if (!Spec.IsValid()) { Error=TEXT("Native cooldown definition is unavailable."); return false; }
                Spec.Data->SetDuration(Remaining,true); Spec.Data->DynamicGrantedTags.AddTag(FGameplayTag::RequestGameplayTag(TEXT("War.Cooldown.DevelopmentStrike")));
                SavedExpiry=int64(Expiry);
            }
        }
        if (Apply)
        {
            const auto Previous=Asc->GetActiveEffects(FGameplayEffectQuery());
            if (Spec.IsValid())
            {
                const auto Applied=Asc->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());auto* Owner=Cast<AWarPlayerState>(Asc->GetOwner());
                if (!Applied.IsValid() || !Owner || !Owner->RestoreCampaignEffectEpoch(Applied,SavedExpiry))
                { if (Applied.IsValid()) Asc->RemoveActiveGameplayEffect(Applied);
                  Error=TEXT("Supported native cooldown application failed; prior effects remain retained."); return false; }
            }
            for (const auto& Handle:Previous) Asc->RemoveActiveGameplayEffect(Handle);
        }
        return true;
    }
}
