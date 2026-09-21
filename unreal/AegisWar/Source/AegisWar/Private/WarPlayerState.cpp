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
    DOREPLIFETIME_CONDITION(AWarPlayerState, Inventory, COND_OwnerOnly);
}

bool AWarPlayerState::GrantRewards(const FGuid& Transaction, const TArray<FWarInventoryItem>& Rewards, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || !Transaction.IsValid() || RewardReceipts.Contains(Transaction)
        || RewardReceipts.Num() >= 65536 || Inventory.Revision == MAX_int32)
    {
        Error = TEXT("Reward transaction is unauthorized, duplicated or exceeds session limits.");
        return false;
    }
    TArray<FWarInventoryItem> Next, Pending;
    if (!WarInventory::PlaceRewards(Inventory.Items, Rewards, Next, Pending, Error)) return false;
    Inventory.Items = MoveTemp(Next);
    Inventory.PendingRewards.Append(Pending);
    ++Inventory.Revision;
    RewardReceipts.Add(Transaction);
    ForceNetUpdate();
    return true;
}

bool AWarPlayerState::ChangeEquipment(const int32 ExpectedRevision, const int32 BagSlot, const bool bEquip, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || ExpectedRevision != Inventory.Revision || Inventory.Revision == MAX_int32)
    {
        Error = TEXT("Inventory changed; refresh before retrying this selection.");
        return false;
    }
    TMap<FName, int32> Equipment;
    for (const auto& Entry : Inventory.Equipment) Equipment.Add(Entry.Slot, Entry.BagSlot);
    if (bEquip)
    {
        if (!WarInventory::Equip(Inventory.Items, BagSlot, Equipment, Error)) return false;
    }
    else
    {
        const auto* Entry = Inventory.Equipment.FindByPredicate([BagSlot](const auto& Row) { return Row.BagSlot == BagSlot; });
        if (!Entry) { Error = TEXT("The selected item is not equipped."); return false; }
        Equipment.Remove(Entry->Slot);
    }
    int32 Strength;
    if (!WarInventory::StrengthBonus(Inventory.Items, Equipment, Strength, Error)) return false;
    Inventory.Equipment.Reset();
    for (const auto& Entry : Equipment)
    {
        FWarEquipmentReference Reference;
        Reference.Slot = Entry.Key; Reference.BagSlot = Entry.Value;
        Inventory.Equipment.Add(Reference);
    }
    ++Inventory.Revision;
    ForceNetUpdate();
    return true;
}

void AWarPlayerState::ServerChangeEquipment_Implementation(const int32 ExpectedRevision, const int32 BagSlot, const bool bEquip)
{
    FString Error;
    ChangeEquipment(ExpectedRevision, BagSlot, bEquip, Error);
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
