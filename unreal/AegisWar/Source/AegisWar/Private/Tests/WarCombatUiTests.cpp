#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCombatUiDrawing.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatUiSettingsTest,"AegisWar.Foundation.CombatUiSettings",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCombatUiSettingsTest::RunTest(const FString& Parameters)
{
    FWarCombatUiSettings S;
    TestEqual(TEXT("Isolated default lifetime"),S.Styles[2].Lifetime,1.f);
    TestEqual(TEXT("Default burst limit"),S.Styles[12].Burst,5.f);
    TestTrue(TEXT("All elements visible by default"),S.Styles[0].Visible && S.Styles[11].Visible && S.Styles[21].Visible);
    auto Changed=S.Styles[2]; Changed.X=23; Changed.Lifetime=2; Changed.Burst=8; Changed.Visible=false;
    S.Set(2,Changed); S.CopySide(2);
    TestEqual(TEXT("Copy reaches corresponding enemy element"),S.Styles[12].X,23.f);
    TestFalse(TEXT("Copy includes visibility"),S.Styles[12].Visible);
    TestTrue(TEXT("Copy leaves other types alone"),S.Styles[13].Visible);
    S.Reset(2); TestEqual(TEXT("Reset element isolated from copy"),S.Styles[12].Lifetime,2.f);
    Changed=S.Styles[12]; Changed.Lifetime=-1; Changed.Rise=129; Changed.Opacity=INFINITY; Changed.Colors[0]=FLinearColor(-1,0,0);
    S.Set(12,Changed);
    TestEqual(TEXT("Invalid lifetime falls back independently"),S.Styles[12].Lifetime,1.f);
    TestEqual(TEXT("Invalid rise falls back"),S.Styles[12].Rise,64.f);
    TestEqual(TEXT("Valid field survives invalid peers"),S.Styles[12].X,23.f);
    TestEqual(TEXT("Invalid color falls back"),S.Styles[12].Colors[0],WarCombatUi::Defaults(12).Colors[0]);
    const FString File=FPaths::ProjectSavedDir()/TEXT("CombatUiTest")/(FGuid::NewGuid().ToString()+TEXT(".ini"));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true); GConfig->Add(File,FConfigFile());
    GConfig->SetString(TEXT("AegisWar.ActionBar"),TEXT("Bars"),TEXT("untouched"),File);
    S.Save(File); GConfig->UnloadFile(File); GConfig->LoadFile(File);
    FWarCombatUiSettings Loaded; Loaded.Load(File);
    TestEqual(TEXT("Disk round trip survives restart"),Loaded.Styles[12].X,23.f);
    TestFalse(TEXT("Visibility persists"),Loaded.Styles[12].Visible);
    GConfig->SetString(TEXT("AegisWar.CombatUi.v1"),TEXT("2"),TEXT("{\"X\":31,\"Lifetime (s)\":999,\"Color0\":\"invalid\"}"),File);
    Loaded.Load(File);
    TestEqual(TEXT("Missing/invalid stored setting uses default"),Loaded.Styles[2].Lifetime,1.f);
    TestEqual(TEXT("Valid stored neighbor survives"),Loaded.Styles[2].X,31.f);
    FWarCombatUiSettings().Save(File); FString Bars;
    GConfig->GetString(TEXT("AegisWar.ActionBar"),TEXT("Bars"),Bars,File);
    TestEqual(TEXT("Combat reset preserves action-bar section"),Bars,FString(TEXT("untouched")));
    GConfig->UnloadFile(File); IFileManager::Get().Delete(*File);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatUiPreviewTest,"AegisWar.Foundation.CombatUiPreview",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCombatUiPreviewTest::RunTest(const FString& Parameters)
{
    FWarCombatUiSettings S; FWarCombatUiPreview A,B;
    A.Replay(1); B.Replay(1);
    for (int I=0;I<20;++I) { A.Advance(.05f,S); B.Advance(.05f,S); TestTrue(TEXT("Shared six-per-recipient cap"),A.Numbers.Num()<=12); }
    TestEqual(TEXT("Exactly twenty procs per side"),A.NextProc,20);
    TestEqual(TEXT("Deterministic playback"),A.Numbers.Num(),B.Numbers.Num());
    if (!A.Numbers.IsEmpty()) TestEqual(TEXT("Deterministic progression"),A.Numbers.Last().Progress,B.Numbers.Last().Progress);
    A.Paused=true; const auto Time=A.Time; A.Advance(.5f,S); TestEqual(TEXT("Pause freezes timeline"),A.Time,Time);
    A.Replay(0); A.Advance(0,S); TestEqual(TEXT("One isolated hit per side"),A.Numbers.Num(),2);
    A.Advance(.99f,S); TestEqual(TEXT("One second lifetime retained"),A.Numbers.Num(),2);
    A.Advance(.02f,S); TestTrue(TEXT("Isolated hits expire"),A.Numbers.IsEmpty());
    S.Styles[4].Visible=false; A.Replay(2); A.Advance(.01f,S);
    TestEqual(TEXT("Hidden friendly healing consumes no slot"),A.Numbers.Num(),1);
    if (!A.Numbers.IsEmpty()) TestTrue(TEXT("Enemy healing keeps enemy style even without actor"),A.Numbers[0].bEnemy);
    S.Styles[14].Lifetime=.25f; A.Replay(2); A.Advance(.3f,S); TestTrue(TEXT("Custom minimum lifetime"),A.Numbers.IsEmpty());
    S=FWarCombatUiSettings(); S.Styles[2].Burst=8; S.Styles[3].Burst=1;
    TArray<FWarFloatingCombatNumber> Numbers;
    for (int I=0;I<20;++I) WarFloatingCombatText::Add(Numbers,1,nullptr,FVector::ZeroVector,I%2?TEXT("CriticalHit"):TEXT("Hit"),99,0,false,&S.Styles[I%2?3:2]);
    TestEqual(TEXT("Independent types share recipient cap"),Numbers.Num(),6);
    for (const auto& N:Numbers) TestEqual(TEXT("Each type retains its own burst limit"),N.Speed,N.Kind==TEXT("Hit")?8.f:1.f);
    WarCombatUi::Move(S,2,FVector2D(20,40),FVector2D(1920,1080),2);
    TestEqual(TEXT("Head relative pixels account for HUD scale"),S.Styles[2].X,10.f);
    WarCombatUi::Move(S,20,FVector2D(192,108),FVector2D(1920,1080),2);
    TestTrue(TEXT("Screen position uses normalized viewport"),FMath::IsNearlyEqual(S.Styles[20].X,.6f));
    S.Styles[5].Scale=2; WarCombatUi::Move(S,6,FVector2D(40,0),FVector2D(1920,1080),2);
    TestEqual(TEXT("Panel child moves relative to parent scale"),S.Styles[6].X,20.f);
    for (FVector2D View:{FVector2D(1280,720),FVector2D(1920,1080),FVector2D(2560,1080)})
    {
        A.Replay(0); A.Advance(.3f,S); auto D=A.Draw(S,View,4);
        TestEqual(TEXT("Hidden elements remain addressable"),D.Handles.Num(),22);
        for (int I:{2,3,4,12,13,14}) TestTrue(TEXT("Number area bounded at supported scale"),D.Handles[I].GetSize().X<=480);
        TestTrue(TEXT("Friendly and enemy panel comparison is readable"),!D.Handles[5].Intersect(D.Handles[15]));
    }
    FWarCombatUiDrawList D; S.Styles[2].Scale=2; S.Styles[2].Font=36; S.Styles[2].Rise=128;
    for (int Lane=0;Lane<3;++Lane) for (float Progress:{0.f,.5f,.999f})
    {
        FWarFloatingCombatNumber N; N.Kind=TEXT("Hit"); N.bEnemy=false; N.Lane=Lane; N.Progress=Progress; N.Amount=1000000000;
        D={}; WarCombatUi::Number(D,S,N,FVector2D(500),1);
        for (const auto& Item:D.Items) TestTrue(TEXT("Extreme text/shadow fits bounded region"),D.Handles[2].IsInsideOrOn(Item.A) && D.Handles[2].IsInsideOrOn(Item.A+Item.B));
    }
    return true;
}
#endif
