#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarInventoryRules.h"

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
#endif
