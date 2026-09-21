#include "WarPlayerState.h"
#include "WarCityNpc.h"
#include "WarCityServices.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"

bool AWarPlayerState::TradeWithCityNpc(const AWarCityNpc* Npc, const FGuid& Transaction, const FName ItemKey,
    const bool bSell, const int32 Quantity, const int32 BagSlot, const int32 ExpectedRevision, FString& Error)
{
    Error = TEXT("Merchant unavailable, transaction duplicated, or inventory changed.");
    if (!HasAuthority() || !CanPerformInventoryAction() || !IsValid(Npc) || !Npc->CanInteract(GetPawn())
        || ExpectedRevision != Inventory.Revision || !Transaction.IsValid()
        || RewardReceipts.Contains(Transaction) || RewardReceipts.Num() >= 65536) return false;
    const auto Offers = WarCityServices::Offers(Npc->GetService());
    const int32* Price = Offers.Find(ItemKey);
    const auto* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    FWarInventoryItem Item;
    if (!Price || !Content || !Content->ResolveInventoryItem(ItemKey, 1, Item)) return false;
    FWarInventorySnapshot Next;
    if (!WarCityServices::Trade(Inventory, Item, *Price, bSell, Quantity, BagSlot, Next, Error)) return false;
    Inventory = MoveTemp(Next);
    RewardReceipts.Add(Transaction);
    ForceNetUpdate();
    return true;
}

void AWarPlayerState::ServerTradeWithCityNpc_Implementation(AWarCityNpc* Npc, FGuid Transaction, FName ItemKey,
    bool bSell, int32 Quantity, int32 BagSlot, int32 ExpectedRevision)
{
    FString Error;
    const bool Accepted = TradeWithCityNpc(Npc, Transaction, ItemKey, bSell, Quantity, BagSlot, ExpectedRevision, Error);
    ClientInventoryResult(Accepted, Error);
}
