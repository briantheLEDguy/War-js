#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarFrontendPresentation.h"
#include "WarCityDefinition.h"
#include "Materials/Material.h"
#include "Engine/Texture2D.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarFrontendPresentationTest, "AegisWar.Foundation.FrontendPresentation",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarFrontendPresentationTest::RunTest(const FString& Parameters)
{
    for (const TCHAR* Name : {TEXT("Logo"), TEXT("Button"), TEXT("Window")})
    {
        const FString Base = TEXT("/Game/UI/Frontend/Artwork/");
        auto* Material = LoadObject<UMaterial>(nullptr, *(Base + TEXT("M_") + Name));
        auto* Texture = LoadObject<UTexture2D>(nullptr, *(Base + TEXT("T_") + Name));
        if (TestNotNull(FString::Printf(TEXT("Installed UI material: %s"), Name), Material))
        {
            TestEqual(TEXT("Artwork renders in Slate"), Material->MaterialDomain, MD_UI);
            TestEqual(TEXT("Ornament transparency is retained"), Material->BlendMode, BLEND_Translucent);
        }
        if (TestNotNull(TEXT("Supplied texture is retained by native content"), Texture))
            TestEqual(TEXT("Artwork uses the UI texture group"), Texture->LODGroup, TEXTUREGROUP_UI);
    }
    FWarFrontendCycle Cycle;
    Cycle.Advance(.1f, false, false, 18, 3);
    TestEqual(TEXT("Loading does not consume the first city view"), Cycle.Time, 0.);
    Cycle.Time = 19.5;
    TestEqual(TEXT("Midpoint is a true half crossfade"), Cycle.Blend(18, 3), .5f);
    Cycle.Advance(.1f, true, true, 18, 3);
    TestEqual(TEXT("Reduced motion holds the current composition"), Cycle.Time, 19.5);
    Cycle.Time = 20.99;
    Cycle.Advance(.02f, true, false, 18, 3);
    TestEqual(TEXT("Aegis transitions to Riftspire"), Cycle.Shot, 1);
    TestTrue(TEXT("New city begins without leftover blend"), FMath::IsNearlyZero(Cycle.Blend(18, 3)));
    Cycle.Time = 20.99; Cycle.Advance(.02f, true, false, 18, 3);
    TestEqual(TEXT("Next Aegis uses its second viewpoint"), Cycle.Shot, 2);
    Cycle.Shot = 3; Cycle.Time = 20.99; Cycle.Advance(.02f, true, false, 18, 3);
    TestEqual(TEXT("Four viewpoints loop"), Cycle.Shot, 0);
    const double Before = Cycle.Time;
    Cycle.Advance(120, true, false, 18, 3);
    TestTrue(TEXT("A resumed window cannot jump through the whole sequence"), Cycle.Time - Before <= .101);

    auto* Definition = NewObject<UWarFrontendPresentationDefinition>();
    FString Error;
    TestFalse(TEXT("Uninstalled cities cannot pass content validation"), Definition->Validate(Error));
    Definition->CharacterComposite = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/UI/Frontend/M_CharacterComposite.M_CharacterComposite")));
    for (FName Zone : {FName(TEXT("aegis_capital")), FName(TEXT("riftspire_capital"))})
    {
        FWarFrontendCity City; City.ZoneId = Zone;
        FWarFrontendShot Shot; Shot.Eye = FVector(1000, 0, 200); Shot.EndEye = FVector(1000, 50, 200);
        City.Shots = {Shot, Shot};
        City.CityDefinition = NewObject<UWarCityDefinition>();
        City.CityDefinition->ZoneId = Zone;
        City.CityDefinition->Revision = TEXT("reviewed-city");
        City.CityDefinition->SceneryLevels.Add(TSoftObjectPtr<UWorld>(FSoftObjectPath(TEXT("/Game/Test/City.City"))));
        Definition->Cities.Add(City);
    }
    TestTrue(TEXT("Complete authored presentation structure is accepted"), Definition->Validate(Error));
    Definition->Cities[1].Shots[0].Target = Definition->Cities[1].Shots[0].Eye;
    TestFalse(TEXT("Degenerate camera is rejected"), Definition->Validate(Error));
    Definition->Cities[1].Shots[0].Target = FVector::ZeroVector;
    const auto DuplicateLevel = Definition->Cities[1].CityDefinition->SceneryLevels[0];
    Definition->Cities[1].CityDefinition->SceneryLevels.Add(DuplicateLevel);
    TestFalse(TEXT("Duplicate shared city attachments are rejected"), Definition->Validate(Error));

    auto* Presentation = NewObject<UWarFrontendPresentation>();
    Presentation->SelectCharacter(TEXT("empire"), TEXT("battle_prelate"), TEXT("m"));
    const uint64 First = Presentation->GetSelectionGeneration();
    Presentation->SelectCharacter(TEXT("greenskin"), TEXT("warbrute"), TEXT("m"));
    TestTrue(TEXT("Changing selection invalidates older asynchronous completions"), Presentation->GetSelectionGeneration() > First);
    TestFalse(TEXT("No model is substituted while a selection is unavailable"), Presentation->HasCharacter());
    const uint64 Last = Presentation->GetSelectionGeneration();
    Presentation->Shutdown();
    TestTrue(TEXT("Shutdown also invalidates pending selections"), Presentation->GetSelectionGeneration() > Last);
    TestNull(TEXT("Shutdown releases city targets"), Presentation->GetCityTarget(0));
    TestNull(TEXT("Out of range target access is safe"), Presentation->GetCityTarget(2));
    TestNull(TEXT("Shutdown releases character material"), Presentation->GetCharacterMaterial());
    return true;
}
#endif
