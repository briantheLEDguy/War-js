#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCharacter.h"
#include "WarGameplayEffects.h"
#include "WarStrikeAbility.h"
#include "AbilitySystemComponent.h"
#include "Net/UnrealNetwork.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"

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

bool AWarPlayerState::ExchangeItems(const FGuid& Transaction, const int32 ExpectedRevision,
    const TMap<int32, int32>& ConsumedSlots, const TArray<FWarInventoryItem>& Outputs, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || ExpectedRevision != Inventory.Revision || Inventory.Revision == MAX_int32
        || !Transaction.IsValid() || RewardReceipts.Contains(Transaction) || RewardReceipts.Num() >= 65536
        || ConsumedSlots.IsEmpty())
    {
        Error = TEXT("Inventory exchange is stale, duplicated or invalid.");
        return false;
    }
    TArray<FWarInventoryItem> Consumed = Inventory.Items;
    for (const auto& Entry : ConsumedSlots)
    {
        auto* Item = Consumed.FindByPredicate([&Entry](const auto& Row) { return Row.Slot == Entry.Key; });
        if (!Item || Entry.Value <= 0 || Entry.Value > Item->Quantity
            || Inventory.Equipment.ContainsByPredicate([&Entry](const auto& Row) { return Row.BagSlot == Entry.Key; }))
        {
            Error = TEXT("Cannot consume missing, insufficient or equipped items.");
            return false;
        }
        Item->Quantity -= Entry.Value;
    }
    Consumed.RemoveAll([](const auto& Item) { return Item.Quantity == 0; });
    TArray<FWarInventoryItem> Next, Overflow;
    if (!WarInventory::PlaceRewards(Consumed, Outputs, Next, Overflow, Error)) return false;
    if (!Overflow.IsEmpty()) { Error = TEXT("Inventory full."); return false; }
    // Deliver previously rolled rewards only after outputs fit. Never regrant their XP/gold or reroll affixes.
    TArray<FWarInventoryItem> Delivered, Pending;
    if (!WarInventory::PlaceRewards(Next, Inventory.PendingRewards, Delivered, Pending, Error)) return false;
    Inventory.Items = MoveTemp(Delivered);
    Inventory.PendingRewards = MoveTemp(Pending);
    ++Inventory.Revision;
    RewardReceipts.Add(Transaction);
    ForceNetUpdate();
    return true;
}

void AWarPlayerState::ServerChangeEquipment_Implementation(const int32 ExpectedRevision, const int32 BagSlot, const bool bEquip)
{
    FString Error;
    const bool bAccepted = ChangeEquipment(ExpectedRevision, BagSlot, bEquip, Error);
    ClientInventoryResult(bAccepted, Error);
}

void AWarPlayerState::ClientInventoryResult_Implementation(const bool bAccepted, const FString& Error)
{
    InventoryMessage = bAccepted ? NSLOCTEXT("AegisWar", "InventoryUpdated", "Inventory updated.") : FText::FromString(Error);
}

bool AWarPlayerState::UseConsumable(const int32 ExpectedRevision, const int32 BagSlot, FString& Error)
{
    Error.Reset();
    if (!HasAuthority() || ExpectedRevision != Inventory.Revision || Attributes->GetHealth() <= 0.f)
    { Error = TEXT("Item use is unavailable or inventory changed."); return false; }
    const auto* Item = Inventory.Items.FindByPredicate([BagSlot](const auto& Row) { return Row.Slot == BagSlot; });
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    float Health, Mana;
    if (!Item || !Item->EquipSlot.IsNone() || !Content || !Content->GetConsumableEffect(Item->Key, Health, Mana))
    { Error = TEXT("The selected item cannot be used."); return false; }
    // Resolve effects from the server catalog. Consumption/reward delivery must succeed before changing attributes.
    if (!ExchangeItems(FGuid::NewGuid(), ExpectedRevision, {{BagSlot, 1}}, {}, Error)) return false;
    AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),
        FMath::Clamp(Attributes->GetHealth() + Health, 0.f, Attributes->GetMaxHealth()));
    AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),
        FMath::Clamp(Attributes->GetMana() + Mana, 0.f, Attributes->GetMaxMana()));
    return true;
}

void AWarPlayerState::ServerUseConsumable_Implementation(const int32 ExpectedRevision, const int32 BagSlot)
{
    FString Error;
    const bool bAccepted = UseConsumable(ExpectedRevision, BagSlot, Error);
    ClientInventoryResult(bAccepted, Error);
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
