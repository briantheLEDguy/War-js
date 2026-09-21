#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarInventoryRules.h"
#include "WarPlayerState.h"
#include "WarCraftingRules.h"
#include "Engine/World.h"

namespace
{
    TArray<FWarInventoryItem> ReadItems(const TArray<TSharedPtr<FJsonValue>>& Values)
    {
        TArray<FWarInventoryItem> Result;
        for (const auto& Value : Values)
        {
            const auto& Json = Value->AsObject();
            FWarInventoryItem Item;
            Item.Key = FName(*Json->GetStringField(TEXT("key")));
            FString Optional;
            if (Json->TryGetStringField(TEXT("kind"), Optional)) Item.Kind = FName(*Optional);
            if (Json->TryGetStringField(TEXT("equipSlot"), Optional)) Item.EquipSlot = FName(*Optional);
            Json->TryGetNumberField(TEXT("slot"), Item.Slot);
            Item.Quantity = Json->GetIntegerField(TEXT("qty"));
            const TSharedPtr<FJsonObject>* Affix = nullptr;
            if (Json->TryGetObjectField(TEXT("affix"), Affix))
            {
                Item.bHasAffix = true;
                Item.StrengthBonus = (*Affix)->GetIntegerField(TEXT("strengthBonus"));
            }
            Result.Add(Item);
        }
        return Result;
    }

    bool SameItems(const TArray<FWarInventoryItem>& A, const TArray<FWarInventoryItem>& B)
    {
        if (A.Num() != B.Num()) return false;
        for (int32 Index = 0; Index < A.Num(); ++Index)
        {
            const auto& Left = A[Index]; const auto& Right = B[Index];
            if (Left.Key != Right.Key || Left.Kind != Right.Kind || Left.EquipSlot != Right.EquipSlot
                || Left.Slot != Right.Slot || Left.Quantity != Right.Quantity
                || Left.bHasAffix != Right.bHasAffix || Left.StrengthBonus != Right.StrengthBonus) return false;
        }
        return true;
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarInventoryParityTest, "AegisWar.Foundation.InventoryRewardParity",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarInventoryParityTest::RunTest(const FString& Parameters)
{
    FString Source;
    const FString Filename = FPaths::Combine(FPaths::ProjectDir(), TEXT("../../migration/fixtures/inventory.json"));
    if (!TestTrue(TEXT("Browser behavior fixtures exist"), FFileHelper::LoadFileToString(Source, *Filename))) return false;
    TSharedPtr<FJsonObject> Root;
    if (!TestTrue(TEXT("Fixtures parse"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Source), Root))) return false;
    TestEqual(TEXT("Fixture schema"), Root->GetIntegerField(TEXT("schemaVersion")), 1);
    const auto& Cases = Root->GetArrayField(TEXT("cases"));
    TestEqual(TEXT("All baseline scenarios execute"), Cases.Num(), 7);
    for (const auto& CaseValue : Cases)
    {
        const auto& Case = CaseValue->AsObject();
        const FString Name = Case->GetStringField(TEXT("name"));
        const auto Inventory = ReadItems(Case->GetArrayField(TEXT("inventory")));
        const auto Rewards = ReadItems(Case->GetArrayField(TEXT("rewards")));
        const auto Expected = Case->GetObjectField(TEXT("expected"));
        TArray<FWarInventoryItem> Result, Pending;
        FString Error;
        TestTrue(Name + TEXT(" applies"), WarInventory::PlaceRewards(Inventory, Rewards, Result, Pending, Error));
        TestTrue(Name + TEXT(" matches inventory"), SameItems(Result, ReadItems(Expected->GetArrayField(TEXT("inventory")))));
        TestTrue(Name + TEXT(" retains pending rewards"), SameItems(Pending, ReadItems(Expected->GetArrayField(TEXT("pendingItems")))));
    }

    FWarInventoryItem Blade;
    Blade.Key = TEXT("test_blade"); Blade.Kind = TEXT("weapon"); Blade.EquipSlot = TEXT("mainHand");
    Blade.Slot = 4; Blade.bHasAffix = true; Blade.StrengthBonus = 7;
    TArray<FWarInventoryItem> Inventory = {Blade};
    TMap<FName, int32> Equipment;
    FString Error;
    TestTrue(TEXT("Gear equips by bag reference"), WarInventory::Equip(Inventory, 4, Equipment, Error));
    TestEqual(TEXT("Equipped gear still occupies bag space"), Inventory.Num(), 1);
    int32 Strength = 0;
    TestTrue(TEXT("Equipment stats resolve from actual bag item"), WarInventory::StrengthBonus(Inventory, Equipment, Strength, Error));
    TestEqual(TEXT("Affix retained"), Strength, 7);
    Inventory.Reset();
    TestFalse(TEXT("Dangling equipment reference cannot grant stats"), WarInventory::StrengthBonus(Inventory, Equipment, Strength, Error));
    Inventory = {Blade, Blade};
    TArray<FWarInventoryItem> Result = {Blade}, Pending = {Blade};
    TestFalse(TEXT("Duplicate bag slots reject transaction"), WarInventory::PlaceRewards(Inventory, {}, Result, Pending, Error));
    TestEqual(TEXT("Rejected transaction leaves output unchanged"), Result.Num(), 1);
    Blade.Quantity = 0;
    TestFalse(TEXT("Zero-quantity reward rejects transaction"), WarInventory::PlaceRewards({}, {Blade}, Result, Pending, Error));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarInventoryAuthorityTest, "AegisWar.Foundation.InventoryAuthority",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarInventoryAuthorityTest::RunTest(const FString& Parameters)
{
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Inventory test world"), World)) return false;
    AWarPlayerState* State = World->SpawnActor<AWarPlayerState>();
    if (!TestNotNull(TEXT("Authoritative player state"), State)) { World->DestroyWorld(false); return false; }
    FWarInventoryItem Blade;
    Blade.Key = TEXT("test_blade"); Blade.Kind = TEXT("weapon"); Blade.EquipSlot = TEXT("mainHand");
    Blade.bHasAffix = true; Blade.StrengthBonus = 7; Blade.Quantity = 25;
    FString Error;
    const FGuid Transaction = FGuid::NewGuid();
    TestTrue(TEXT("Trusted grant accepts full bag and deferred gear"), State->GrantRewards(Transaction, {Blade}, Error));
    TestEqual(TEXT("Exactly 24 bag slots"), State->GetInventory().Items.Num(), 24);
    TestEqual(TEXT("Rolled overflow retained"), State->GetInventory().PendingRewards.Num(), 1);
    TestEqual(TEXT("Deferred affix retained"), State->GetInventory().PendingRewards[0].StrengthBonus, 7);
    TestFalse(TEXT("Retry cannot duplicate items or pending rewards"), State->GrantRewards(Transaction, {Blade}, Error));
    TestEqual(TEXT("Duplicate does not advance revision"), State->GetInventory().Revision, 1);
    TestFalse(TEXT("Fabricated slot rejected"), State->ChangeEquipment(1, 99, true, Error));
    TestTrue(TEXT("Owned item equips"), State->ChangeEquipment(1, 0, true, Error));
    TestFalse(TEXT("Stale unequip rejected"), State->ChangeEquipment(1, 0, false, Error));
    TestEqual(TEXT("Rejected request preserves equipment"), State->GetInventory().Equipment.Num(), 1);
    TestTrue(TEXT("Current revision unequips"), State->ChangeEquipment(2, 0, false, Error));
    TestEqual(TEXT("Unequip keeps bag occupancy"), State->GetInventory().Items.Num(), 24);
    TestEqual(TEXT("Equipment reference removed"), State->GetInventory().Equipment.Num(), 0);
    Blade.Quantity = 0;
    const FGuid InvalidTransaction = FGuid::NewGuid();
    TestFalse(TEXT("Invalid reward is atomic"), State->GrantRewards(InvalidTransaction, {Blade}, Error));
    Blade.Quantity = 1;
    TestTrue(TEXT("Rejected reward did not consume receipt"), State->GrantRewards(InvalidTransaction, {Blade}, Error));
    AWarPlayerState* Exchange = World->SpawnActor<AWarPlayerState>();
    FWarInventoryItem Potion;
    Potion.Key = TEXT("test_potion"); Potion.Kind = TEXT("consumable"); Potion.Quantity = 99;
    Blade.Quantity = 24;
    TestTrue(TEXT("Exchange seed fills bag with one deferred blade"), Exchange->GrantRewards(FGuid::NewGuid(), {Potion, Blade}, Error));
    Blade.Quantity = 1;
    const FGuid ExchangeId = FGuid::NewGuid();
    TestFalse(TEXT("Full-bag output rolls consumption back"), Exchange->ExchangeItems(ExchangeId, 1, {{0, 1}}, {Blade}, Error));
    TestEqual(TEXT("Failed output preserves ingredients"), Exchange->GetInventory().Items[0].Quantity, 99);
    TestEqual(TEXT("Failed output preserves revision"), Exchange->GetInventory().Revision, 1);
    TestFalse(TEXT("Invalid quantity cannot create ingredients"), Exchange->ExchangeItems(ExchangeId, 1, {{0, -1}}, {}, Error));
    TestTrue(TEXT("Freed slot delivers pending rolled reward"), Exchange->ExchangeItems(ExchangeId, 1, {{0, 99}}, {}, Error));
    TestEqual(TEXT("Deferred reward delivered exactly once"), Exchange->GetInventory().PendingRewards.Num(), 0);
    TestEqual(TEXT("Bag remains full after delivery"), Exchange->GetInventory().Items.Num(), 24);
    const auto* Delivered = Exchange->GetInventory().Items.FindByPredicate([](const auto& Item) { return Item.Slot == 0; });
    TestTrue(TEXT("Delivery retains rolled affix"), Delivered && Delivered->StrengthBonus == 7 && Delivered->bHasAffix);
    TestFalse(TEXT("Duplicate exchange cannot consume again"), Exchange->ExchangeItems(ExchangeId, 2, {{0, 1}}, {}, Error));
    TestTrue(TEXT("Equip item before protected consumption"), Exchange->ChangeEquipment(2, 0, true, Error));
    TestFalse(TEXT("Equipped gear cannot be consumed"), Exchange->ExchangeItems(FGuid::NewGuid(), 3, {{0, 1}}, {}, Error));
    AWarPlayerState* Salvage = World->SpawnActor<AWarPlayerState>();
    Blade.Quantity = 24;
    TestTrue(TEXT("Fill bag with gear for salvage rollback"), Salvage->GrantRewards(FGuid::NewGuid(), {Blade}, Error));
    Blade.Quantity = 1;
    TArray<FWarInventoryItem> SalvageOutputs;
    TestTrue(TEXT("Affixed blade produces three salvage outputs"), WarCrafting::SalvageOutputs(Blade, SalvageOutputs, Error));
    TestEqual(TEXT("Scrap, fragments and essence"), SalvageOutputs.Num(), 3);
    TestFalse(TEXT("One freed slot cannot discard two salvage outputs"), Salvage->ExchangeItems(FGuid::NewGuid(), 1, {{0, 1}}, SalvageOutputs, Error));
    TestEqual(TEXT("Failed salvage retains all gear"), Salvage->GetInventory().Items.Num(), 24);
    TestEqual(TEXT("Failed salvage retains original revision"), Salvage->GetInventory().Revision, 1);
    TestTrue(TEXT("Failed salvage does not turn outputs into deferred rewards"), Salvage->GetInventory().PendingRewards.IsEmpty());
    World->DestroyWorld(false);
    return true;
}
#endif
