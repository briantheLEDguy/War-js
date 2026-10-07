#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarImportLibrary.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"
#include <limits>

namespace
{
    TSharedPtr<FJsonObject> ReadVector(UMaterialExpressionVectorParameter* Expression)
    {
        TSharedPtr<FJsonObject> Json;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeVectorParameter(Expression)),Json);
        return Json;
    }
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarVectorParameterReadback,"AegisWar.Foundation.CitadelVectorParameterReadback",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarVectorParameterReadback::RunTest(const FString&)
{
    auto* Material=NewObject<UMaterial>(GetTransientPackage());
    auto* Node=NewObject<UMaterialExpressionVectorParameter>(Material);
    Node->ParameterName=TEXT("Base_Color_Tint");Node->DefaultValue=FLinearColor(.37f,.4f,.44f,1.f);
    Node->Group=TEXT("Mountain");Node->SortPriority=-3;Node->ExpressionGUID=FGuid(1,2,3,4);
    Node->bUseCustomPrimitiveData=true;Node->PrimitiveDataIndex=7;
    Node->ChannelNames.R=NSLOCTEXT("WarVectorReadback","Red","Tint");
    Node->ChannelNames.G=NSLOCTEXT("WarVectorReadback","Green","Tint");
    Node->ChannelNames.B=FText::AsCultureInvariant(TEXT("Blue"));Node->ChannelNames.A=FText::GetEmpty();
    const bool WasDirty=Material->GetPackage()->IsDirty();const auto Json=ReadVector(Node);
    if (!TestTrue(TEXT("JSON"),Json.IsValid())) return false;
    TestTrue(TEXT("Native readback available"),Json->GetBoolField(TEXT("available")));
    TestTrue(TEXT("Read only"),Json->GetBoolField(TEXT("readOnly")));
    const auto V=Json->GetObjectField(TEXT("values"));TestEqual(TEXT("Eight exact profile values"),V->Values.Num(),8);
    TestEqual(TEXT("Name"),V->GetStringField(TEXT("parameter_name")),FString(TEXT("Base_Color_Tint")));
    TestEqual(TEXT("Group"),V->GetStringField(TEXT("group")),FString(TEXT("Mountain")));
    TestEqual(TEXT("Sort priority"),V->GetIntegerField(TEXT("sort_priority")),-3);
    TestEqual(TEXT("Meaningful GUID"),V->GetStringField(TEXT("expression_guid")),Node->ExpressionGUID.ToString(EGuidFormats::Digits));
    TestEqual(TEXT("Default red float"),V->GetArrayField(TEXT("default_value"))[0]->AsNumber(),double(Node->DefaultValue.R));
    TestTrue(TEXT("Primitive source flag observed"),V->GetBoolField(TEXT("use_custom_primitive_data")));
    TestEqual(TEXT("Primitive source index observed"),V->GetIntegerField(TEXT("primitive_data_index")),7);
    const auto Channels=V->GetObjectField(TEXT("channel_names"));
    TestEqual(TEXT("Four channel histories"),Channels->Values.Num(),4);
    TestEqual(TEXT("Equal display strings"),Channels->GetObjectField(TEXT("r"))->GetStringField(TEXT("display")),Channels->GetObjectField(TEXT("g"))->GetStringField(TEXT("display")));
    TestNotEqual(TEXT("Different localization identities survive"),Channels->GetObjectField(TEXT("r"))->GetStringField(TEXT("history")),Channels->GetObjectField(TEXT("g"))->GetStringField(TEXT("history")));
    const FString Before=UWarImportLibrary::DescribeVectorParameter(Node);
    TestEqual(TEXT("Repeated native read stable"),UWarImportLibrary::DescribeVectorParameter(Node),Before);
    TestEqual(TEXT("Dirty state unchanged"),Material->GetPackage()->IsDirty(),WasDirty);
    auto* Copy=DuplicateObject<UMaterialExpressionVectorParameter>(Node,NewObject<UMaterial>(GetTransientPackage()));
    const auto Copied=ReadVector(Copy);
    FString A,B;FJsonSerializer::Serialize(V.ToSharedRef(),TJsonWriterFactory<>::Create(&A));
    FJsonSerializer::Serialize(Copied->GetObjectField(TEXT("values")).ToSharedRef(),TJsonWriterFactory<>::Create(&B));
    TestEqual(TEXT("Copy preserves all eight values and histories"),B,A);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarVectorParameterReadbackBounds,"AegisWar.Foundation.CitadelVectorParameterReadbackBounds",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarVectorParameterReadbackBounds::RunTest(const FString&)
{
    TestFalse(TEXT("Null unavailable"),ReadVector(nullptr)->GetBoolField(TEXT("available")));
    auto* Node=NewObject<UMaterialExpressionVectorParameter>(GetTransientPackage());Node->ExpressionGUID=FGuid();
    TestFalse(TEXT("No inferred replacement for missing GUID"),ReadVector(Node)->GetBoolField(TEXT("available")));
    Node->ExpressionGUID=FGuid(1,2,3,4);Node->DefaultValue.R=std::numeric_limits<float>::quiet_NaN();
    TestFalse(TEXT("Nonfinite unavailable"),ReadVector(Node)->GetBoolField(TEXT("available")));
    Node->DefaultValue=FLinearColor::White;Node->ChannelNames.R=FText::FromString(FString::ChrN(4097,TEXT('x')));
    TestFalse(TEXT("Oversize FText history unavailable"),ReadVector(Node)->GetBoolField(TEXT("available")));
    return true;
}
#endif
