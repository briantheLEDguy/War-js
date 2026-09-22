#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarMenuFrameLayout.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMenuFrameTest,"AegisWar.Foundation.MenuFrame",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarMenuFrameTest::RunTest(const FString& Parameters)
{
    for (const FVector2D Size:{FVector2D(1160,840),FVector2D(540,650),FVector2D(560,1200),FVector2D(120,90)})
    {
        const auto Layout=WarMenuFrame::Layout(Size,.2);
        TestEqual(TEXT("Full width covered"),Layout.X[5],Size.X);
        TestEqual(TEXT("Full height covered"),Layout.Y[3],Size.Y);
        for (int32 I=0;I<5;++I) TestTrue(TEXT("Columns never overlap"),Layout.X[I+1]>=Layout.X[I]);
        for (int32 I=0;I<3;++I) TestTrue(TEXT("Rows never overlap"),Layout.Y[I+1]>=Layout.Y[I]);
        TestTrue(TEXT("Crest stays centred"),FMath::IsNearlyEqual((Layout.X[2]+Layout.X[3])/2,Size.X/2));
        TestTrue(TEXT("Crest aspect preserved"),FMath::IsNearlyEqual((Layout.X[3]-Layout.X[2])/372,Layout.Y[1]/460));
    }
    const auto Short=WarMenuFrame::Layout(FVector2D(560,650),.2),Tall=WarMenuFrame::Layout(FVector2D(560,1200),.2);
    TestEqual(TEXT("Tall panels keep original top ornament height"),Short.Y[1],Tall.Y[1]);
    TestEqual(TEXT("Only middle grows vertically"),Tall.Y[2]-Short.Y[2],550.);
    TArray<uint8> Bytes;
    TestTrue(TEXT("Menu art is staged at runtime content path"),FFileHelper::LoadFileToArray(Bytes,*FPaths::Combine(FPaths::ProjectContentDir(),TEXT("UI/menuback.png"))));
    TestEqual(TEXT("Original PNG size retained"),Bytes.Num(),1756321);
    return true;
}
#endif
