#include "WarAttributeSet.h"
#include "WarCharacter.h"
#include "WarCombatStatus.h"
#include "WarSiegeGameMode.h"
#include "WarWrathRelic.h"
#include "WarPlayerState.h"
#include "GameplayEffectExtension.h"
#include "Net/UnrealNetwork.h"

void UWarAttributeSet::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, Health, COND_None, REPNOTIFY_Always);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, MaxHealth, COND_None, REPNOTIFY_Always);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, Mana, COND_OwnerOnly, REPNOTIFY_Always);
    DOREPLIFETIME_CONDITION_NOTIFY(UWarAttributeSet, MaxMana, COND_OwnerOnly, REPNOTIFY_Always);
}

void UWarAttributeSet::PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue)
{
    Super::PreAttributeChange(Attribute, NewValue);
    if (!FMath::IsFinite(NewValue)) NewValue = 0.f;
    if (Attribute == GetHealthAttribute()) NewValue = FMath::Clamp(NewValue, 0.f, GetMaxHealth());
    if (Attribute == GetManaAttribute()) NewValue = FMath::Clamp(NewValue, 0.f, GetMaxMana());
    if (Attribute == GetMaxHealthAttribute() || Attribute == GetMaxManaAttribute()) NewValue = FMath::Max(1.f, NewValue);
}

bool UWarAttributeSet::PreGameplayEffectExecute(FGameplayEffectModCallbackData& Data)
{
    if (!Super::PreGameplayEffectExecute(Data)) return false;
    if (Data.EvaluatedData.Attribute == GetHealthAttribute()) HealthBeforeEffect = GetHealth();
    if (auto* Siege = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>(); Siege && Data.EvaluatedData.Attribute == GetHealthAttribute())
    {
        auto* Avatar = GetOwningAbilitySystemComponent()->GetAvatarActor();
        if (Data.EvaluatedData.Magnitude < 0 && (Siege->IsProtected(Avatar) || Siege->IsProtected(Data.EffectSpec.GetContext().GetInstigator()))) return false;
        if (const auto* Unit = Cast<AWarSiegeCharacter>(Avatar); Unit && Unit->Unit == EWarSiegeUnit::Commander && Data.EvaluatedData.Magnitude > 0) return false;
    }
    if (Data.EvaluatedData.Attribute == GetHealthAttribute() && Data.EvaluatedData.Magnitude < 0)
        if (auto* Status = UWarCombatStatus::On(GetOwningAbilitySystemComponent()->GetAvatarActor()))
            Data.EvaluatedData.Magnitude = -Status->ReceiveDamage(-Data.EvaluatedData.Magnitude);
    return true;
}

void UWarAttributeSet::PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data)
{
    Super::PostGameplayEffectExecute(Data);
    if (Data.EvaluatedData.Attribute == GetHealthAttribute())
    {
        if (Data.EvaluatedData.Magnitude < 0)
            if (const auto* Unit = Cast<AWarSiegeCharacter>(GetOwningAbilitySystemComponent()->GetAvatarActor()); Unit && Unit->Unit == EWarSiegeUnit::Commander)
                if (auto* Siege = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>()) Siege->CommanderDamaged();
        SetHealth(FMath::Clamp(GetHealth(), 0.f, GetMaxHealth()));
        const float HealthLost = FMath::Max(0.f, HealthBeforeEffect - GetHealth());
        auto* Dealer = Cast<AWarCharacter>(Data.EffectSpec.GetContext().GetInstigator());
        const auto* Victim = Cast<AWarCharacter>(GetOwningAbilitySystemComponent()->GetAvatarActor());
        const auto* DealerState = Dealer ? Dealer->GetPlayerState<AWarPlayerState>() : nullptr;
        const auto* VictimState = Victim ? Victim->GetPlayerState<AWarPlayerState>() : nullptr;
        if (Data.EvaluatedData.Magnitude < 0 && DealerState && VictimState && DealerState->GetRealm() != EWarRealm::None
            && VictimState->GetRealm() != EWarRealm::None && DealerState->GetRealm() != VictimState->GetRealm()
            && DealerState->GetCurrentZone() == VictimState->GetCurrentZone()) AWarWrathRelic::HostileHealthDamage(Dealer, HealthLost);
        if (HealthLost > 0 && GetHealth() > 0)
            if (auto* Avatar = Cast<AWarCharacter>(GetOwningAbilitySystemComponent()->GetAvatarActor()))
                Avatar->ReactToHit(Data.EffectSpec.GetContext().GetInstigator(), HealthLost);
        if (GetHealth() <= 0.f)
        {
            if (AWarCharacter* Avatar = Cast<AWarCharacter>(GetOwningAbilitySystemComponent()->GetAvatarActor()))
                Avatar->HandleDeath();
        }
    }
    if (Data.EvaluatedData.Attribute == GetManaAttribute()) SetMana(FMath::Clamp(GetMana(), 0.f, GetMaxMana()));
}

void UWarAttributeSet::OnRep_Health(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, Health, Previous); }
void UWarAttributeSet::OnRep_MaxHealth(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, MaxHealth, Previous); }
void UWarAttributeSet::OnRep_Mana(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, Mana, Previous); }
void UWarAttributeSet::OnRep_MaxMana(const FGameplayAttributeData& Previous) { GAMEPLAYATTRIBUTE_REPNOTIFY(UWarAttributeSet, MaxMana, Previous); }
