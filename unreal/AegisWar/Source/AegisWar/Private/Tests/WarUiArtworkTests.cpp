#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "ImageUtils.h"
#include "Engine/Texture2D.h"
#include "WarAbilityBarLayout.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarUiArtworkTest,"AegisWar.Foundation.UiArtwork",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarUiArtworkTest::RunTest(const FString& Parameters)
{
    struct FAsset { const TCHAR* Name; int32 Width; int32 Height; };
    const FAsset Assets[] = {
        {TEXT("abilitybarsingle.png"),1254,1254},
        {TEXT("leftendcap-abilitybar.png"),1374,1145},
        {TEXT("rightendcap-abilitybar.png"),1374,1145},
        {TEXT("healthbar.png"),2172,724},
        {TEXT("minimap.png"),1254,1254},
        {TEXT("window.png"),1086,1448}};
    for (const auto& Asset : Assets)
    {
        const FString RuntimePath = FPaths::Combine(FPaths::ProjectContentDir(),TEXT("UI"),Asset.Name);
        UTexture2D* Decoded = FImageUtils::ImportFileAsTexture2D(RuntimePath);
        if (TestNotNull(FString::Printf(TEXT("Runtime PNG decodes: %s"),Asset.Name),Decoded))
        {
            TestEqual(TEXT("UV source width matches original"),Decoded->GetSizeX(),Asset.Width);
            TestEqual(TEXT("UV source height matches original"),Decoded->GetSizeY(),Asset.Height);
        }
        TArray<uint8> Original,Runtime;
        const FString SourcePath = FPaths::Combine(FPaths::ProjectDir(),TEXT("graphics-new"),Asset.Name);
        TestTrue(TEXT("Supplied image available"),FFileHelper::LoadFileToArray(Original,*SourcePath));
        TestTrue(TEXT("Staged image available"),FFileHelper::LoadFileToArray(Runtime,*RuntimePath));
        TestTrue(TEXT("Artwork copied without modification"),!Original.IsEmpty() && Original == Runtime);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarAbilityArtworkLayoutTest,"AegisWar.Foundation.AbilityArtworkLayout",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarAbilityArtworkLayoutTest::RunTest(const FString& Parameters)
{
    using namespace WarAbilityBarLayout;
    for (int32 Count=1;Count<=10;++Count)
    {
        const auto Padding = WarAbilityBarLayout::Padding(Count);
        for (int32 Index=0;Index<Count;++Index)
        {
            const auto Art = Artwork(Index,Count);
            const FVector2D Scale(InnerSize/Art.Inner.GetSize().X,InnerSize/Art.Inner.GetSize().Y);
            const FVector2D PaintedInner = Art.Inner.GetSize()*Scale;
            TestTrue(TEXT("Every inner ability is the same exact square"),PaintedInner.Equals(FVector2D(InnerSize),.0001));
            const FVector2D Min = FVector2D((Pitch-InnerSize)/2,0)+(Art.Visible.Min-Art.Inner.Min)*Scale;
            const FVector2D Max = FVector2D((Pitch-InnerSize)/2,0)+(Art.Visible.Max-Art.Inner.Min)*Scale;
            if (Index>0) TestTrue(TEXT("Shared left rail meets previous cell"),FMath::IsNearlyZero(Min.X,.0001));
            if (Index<Count-1) TestTrue(TEXT("Shared right rail meets next cell"),FMath::IsNearlyEqual(Max.X,Pitch,.0001));
            TestTrue(TEXT("All ornaments remain within draggable bar bounds"),Min.X+Index*Pitch+Padding.Left>=0
                && Max.X+Index*Pitch+Padding.Left<=Size(Count).X && Min.Y+Padding.Top>=0 && Max.Y<=InnerSize+Padding.Bottom);
        }
        for (const FVector2D View : {FVector2D(320,240),FVector2D(1280,800),FVector2D(3840,2160)})
        {
            const auto Fitted = Fit(View,Count);
            TestTrue(TEXT("Whole decorated bar fits viewport"),Fitted.X<=View.X && Fitted.Y<=View.Y);
            TestTrue(TEXT("Viewport fit preserves proportions"),FMath::IsNearlyEqual(Fitted.X/Size(Count).X,Fitted.Y/Size(Count).Y));
        }
    }
    return true;
}
#endif
