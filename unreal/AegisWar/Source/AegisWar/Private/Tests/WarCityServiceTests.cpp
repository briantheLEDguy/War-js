#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCityServices.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCityServiceTest,"AegisWar.Foundation.CityServices",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCityServiceTest::RunTest(const FString& Parameters)
{
    FWarInventorySnapshot Current, Next; FString Error;
    Current.CharacterProgression.Gold=20;
    FWarInventoryItem Bread; Bread.Key=TEXT("bread"); Bread.Kind=TEXT("consumable"); Bread.Quantity=1;
    TestTrue(TEXT("Buy uses gold and bag atomically"),WarCityServices::Trade(Current,Bread,2,false,3,INDEX_NONE,Next,Error));
    TestEqual(TEXT("Buy debits six gold"),Next.CharacterProgression.Gold,static_cast<int64>(14));
    TestEqual(TEXT("Bought quantity"),Next.Items[0].Quantity,3);
    TestEqual(TEXT("Revision increments once"),Next.Revision,1);
    Current=Next;
    TestTrue(TEXT("Sell uses half price"),WarCityServices::Trade(Current,Bread,2,true,2,Current.Items[0].Slot,Next,Error));
    TestEqual(TEXT("Sale credits two gold"),Next.CharacterProgression.Gold,static_cast<int64>(16));
    TestFalse(TEXT("Insufficient gold rejected"),WarCityServices::Trade(Current,Bread,10,false,3,INDEX_NONE,Next,Error));
    TestEqual(TEXT("Failed trade leaves caller snapshot intact"),Current.CharacterProgression.Gold,static_cast<int64>(14));
    TestFalse(TEXT("Wrong slot rejected"),WarCityServices::Trade(Current,Bread,2,true,1,23,Next,Error));
    TestFalse(TEXT("Negative quantity rejected"),WarCityServices::Trade(Current,Bread,2,false,-1,INDEX_NONE,Next,Error));
    TestFalse(TEXT("Overselling rejected"),WarCityServices::Trade(Current,Bread,2,true,4,Current.Items[0].Slot,Next,Error));
    FWarEquipmentReference Ref;Ref.Slot=TEXT("head");Ref.BagSlot=Current.Items[0].Slot;Current.Equipment.Add(Ref);
    TestFalse(TEXT("Equipped slot cannot be sold"),WarCityServices::Trade(Current,Bread,2,true,1,Ref.BagSlot,Next,Error));
    Current.Equipment.Reset();Current.Items.Reset();Current.CharacterProgression.Gold=100;
    for (int32 Slot=0;Slot<WarInventory::Capacity;++Slot)
    { auto Item=Bread;Item.Key=FName(*FString::Printf(TEXT("filler_%d"),Slot));Item.Slot=Slot;Current.Items.Add(Item); }
    TestFalse(TEXT("Full bags cannot consume gold"),WarCityServices::Trade(Current,Bread,2,false,1,INDEX_NONE,Next,Error));
    TestEqual(TEXT("Gold preserved on capacity failure"),Current.CharacterProgression.Gold,static_cast<int64>(100));
    TestEqual(TEXT("Quartermaster has three goods"),WarCityServices::Offers(TEXT("quartermaster")).Num(),3);
    TestTrue(TEXT("Teachers cannot trade"),WarCityServices::Offers(TEXT("class_teacher")).IsEmpty());
    TestTrue(TEXT("Unknown NPC cannot advertise services"),WarCityServices::ServiceForNpc(TEXT("fake_merchant")).IsNone());
    return true;
}
#endif
