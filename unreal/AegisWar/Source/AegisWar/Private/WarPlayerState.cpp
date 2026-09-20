#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCharacter.h"
#include "WarGameplayEffects.h"
#include "WarStrikeAbility.h"
#include "AbilitySystemComponent.h"
#include "Net/UnrealNetwork.h"

AWarPlayerState::AWarPlayerState()
{
    AbilitySystem = CreateDefaultSubobject<UAbilitySystemComponent>(TEXT("AbilitySystem"));
    AbilitySystem->SetIsReplicated(true);
    AbilitySystem->SetReplicationMode(EGameplayEffectReplicationMode::Mixed);
    Attributes = CreateDefaultSubobject<UWarAttributeSet>(TEXT("Attributes"));
    SetNetUpdateFrequency(30.f);
}

UAbilitySystemComponent* AWarPlayerState::GetAbilitySystemComponent() const { return AbilitySystem; }

void AWarPlayerState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarPlayerState, Realm);
}

void AWarPlayerState::SetDevelopmentRealm(const EWarRealm InRealm)
{
    if (HasAuthority() && Realm == EWarRealm::None && InRealm != EWarRealm::None) Realm = InRealm;
}

void AWarPlayerState::InitializeForPawn(AWarCharacter* Avatar)
{
    AbilitySystem->InitAbilityActorInfo(this, Avatar);
    if (!HasAuthority() || !Avatar || !Avatar->IsVisualReady()) return;
    AbilitySystem->ApplyGameplayEffectToSelf(GetDefault<UWarInitialAttributesEffect>(), 1.f, AbilitySystem->MakeEffectContext());
    if (!bGrantedDevelopmentAbility)
    {
        AbilitySystem->GiveAbility(FGameplayAbilitySpec(UWarStrikeAbility::StaticClass(), 1));
        bGrantedDevelopmentAbility = true;
    }
}
